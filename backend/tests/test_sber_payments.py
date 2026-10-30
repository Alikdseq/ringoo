"""Тесты эквайринга Сбера (только моки HTTP, без реального шлюза)."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import (
    PaymentError,
    apply_late_payment_policy,
    expire_unpaid_online_orders,
    find_hung_payments,
    handle_sber_callback,
    initiate_sber_payment,
    reconcile_open_payments,
    sync_payment_from_bank,
)
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from integrations.sber.client import SberEcomClient, SberEcomError


class _FakeHTTPResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status
        self.headers = {"Content-Type": "application/json"}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _order(**kwargs):
    cat = Category.objects.create(title="Cat", slug=f"c-{Category.objects.count()}")
    product = Product.objects.create(
        title="Phone",
        slug=f"p-{Product.objects.count()}",
        price=Decimal("1000.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"s-{Store.objects.count()}", address="a", city="c"
    )
    Stock.objects.create(product=product, store=store, quantity=10, reserved_quantity=1)
    defaults = dict(
        full_name="Иван Иванов",
        phone="79001112233",
        email="test@example.com",
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=Order.PAYMENT_ONLINE,
        status=Order.STATUS_NEW,
        total_amount=Decimal("1000.00"),
        delivery_cost=Decimal("0"),
        consent_personal_data=True,
    )
    defaults.update(kwargs)
    order = Order.objects.create(**defaults)
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=1,
        price=Decimal("1000.00"),
        item_total=Decimal("1000.00"),
    )
    return order, product, store


@override_settings(
    SBER_ECOM_ENABLED=True,
    SBER_ECOM_USERNAME="test-api",
    SBER_ECOM_PASSWORD="secret",
    SBER_ECOM_BASE_URL="https://ecomtest.sberbank.ru",
    FRONTEND_URL="https://shop.test",
    ONLINE_PAYMENT_TIMEOUT_MINUTES=20,
)
class SberClientTests(TestCase):
    def test_disabled_raises(self):
        client = SberEcomClient(enabled=False)
        with self.assertRaises(SberEcomError):
            client.register_order(
                order_number="x",
                amount_kopecks=100,
                return_url="https://shop.test/ok",
            )

    def test_production_url_blocked_without_allow_flag(self):
        with self.assertRaises(SberEcomError) as ctx:
            SberEcomClient(
                enabled=True,
                base_url="https://epay.sberbank.ru",
                username="u",
                password="p",
                allow_production=False,
            )
        self.assertIn("ALLOW_PRODUCTION", str(ctx.exception))

    def test_production_url_allowed_with_flag(self):
        client = SberEcomClient(
            enabled=False,
            base_url="https://epay.sberbank.ru",
            username="u",
            password="p",
            allow_production=True,
        )
        self.assertTrue(client.allow_production)
        with self.assertRaises(SberEcomError):
            # всё ещё disabled → сеть не вызывается
            client.register_order(
                order_number="x",
                amount_kopecks=100,
                return_url="https://shop.test/ok",
            )

    def test_default_base_is_ecomtest_not_epay(self):
        client = SberEcomClient(enabled=False, username="u", password="p")
        self.assertIn("ecomtest", client.base_url)
        self.assertNotIn("epay.sberbank.ru", client.base_url)

    def test_register_success(self):
        client = SberEcomClient(
            enabled=True,
            base_url="https://ecomtest.sberbank.ru",
            username="u",
            password="p",
        )
        body = {
            "errorCode": "0",
            "orderId": "a67b0ced-c9a4-4cfb-bce3-b9595afaafc1",
            "formUrl": "https://ecomtest.sberbank.ru/pp/pay_ru?orderId=a67b0ced-c9a4-4cfb-bce3-b9595afaafc1",
        }
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            payload = json.loads(req.data.decode("utf-8"))
            captured["payload"] = payload
            self.assertNotIn("password", str(captured["url"]))
            return _FakeHTTPResponse(json.dumps(body).encode())

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.register_order(
                order_number="abc123",
                amount_kopecks=100000,
                return_url="https://shop.test/ok",
                fail_url="https://shop.test/fail",
            )
        self.assertEqual(result["orderId"], body["orderId"])
        self.assertTrue(result["formUrl"].startswith("https://"))
        self.assertEqual(captured["payload"]["amount"], 100000)
        self.assertEqual(captured["payload"]["userName"], "u")
        self.assertEqual(captured["payload"]["password"], "p")

    def test_register_gateway_error(self):
        client = SberEcomClient(
            enabled=True, base_url="https://ecomtest.sberbank.ru", username="u", password="p"
        )
        body = {"errorCode": "5", "errorMessage": "Доступ запрещен"}
        with patch(
            "urllib.request.urlopen",
            return_value=_FakeHTTPResponse(json.dumps(body).encode()),
        ):
            with self.assertRaises(SberEcomError) as ctx:
                client.register_order(
                    order_number="x",
                    amount_kopecks=100,
                    return_url="https://shop.test/ok",
                )
        self.assertEqual(ctx.exception.error_code, "5")

    def test_reverse_success(self):
        client = SberEcomClient(
            enabled=True, base_url="https://ecomtest.sberbank.ru", username="u", password="p"
        )
        body = {"errorCode": "0"}
        with patch(
            "urllib.request.urlopen",
            return_value=_FakeHTTPResponse(json.dumps(body).encode()),
        ):
            data = client.reverse_order(order_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self.assertEqual(data.get("errorCode"), "0")


@override_settings(
    SBER_ECOM_ENABLED=True,
    FRONTEND_URL="https://shop.test",
    ONLINE_PAYMENT_TIMEOUT_MINUTES=20,
)
class PaymentServiceTests(TestCase):
    def test_initiate_uses_db_amount_not_client(self):
        order, _, _ = _order(total_amount=Decimal("1999.50"))
        mock_client = MagicMock()
        mock_client.register_order.return_value = {
            "orderId": "11111111-1111-1111-1111-111111111111",
            "formUrl": "https://ecomtest.sberbank.ru/pp/pay",
            "raw": {"errorCode": "0"},
        }
        result = initiate_sber_payment(order, client=mock_client)
        self.assertEqual(result.payment.amount_kopecks, 199950)
        kwargs = mock_client.register_order.call_args.kwargs
        self.assertEqual(kwargs["amount_kopecks"], 199950)
        self.assertIn(str(order.id), kwargs["return_url"])

    def test_initiate_rejects_non_online(self):
        order, _, _ = _order(payment_type=Order.PAYMENT_CASH)
        with self.assertRaises(PaymentError) as ctx:
            initiate_sber_payment(order, client=MagicMock())
        self.assertEqual(ctx.exception.code, "not_online")

    def test_already_paid_blocks_second_register(self):
        order, _, _ = _order()
        Payment.objects.create(
            order=order,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="paid1",
            sber_order_id="22222222-2222-2222-2222-222222222222",
            paid_at=timezone.now(),
        )
        with self.assertRaises(PaymentError) as ctx:
            initiate_sber_payment(order, client=MagicMock())
        self.assertEqual(ctx.exception.code, "already_paid")

    def test_reuse_active_form_url(self):
        order, _, _ = _order()
        Payment.objects.create(
            order=order,
            status=Payment.STATUS_REGISTERED,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="reuse1",
            sber_order_id="33333333-3333-3333-3333-333333333333",
            form_url="https://ecomtest.sberbank.ru/pp/existing",
        )
        mock_client = MagicMock()
        result = initiate_sber_payment(order, client=mock_client)
        self.assertTrue(result.reused)
        mock_client.register_partner = mock_client  # silence
        mock_client.register_order.assert_not_called()

    def test_sync_marks_paid_and_confirms_order(self):
        order, _, _ = _order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_REGISTERED,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="sync1",
            sber_order_id="44444444-4444-4444-4444-444444444444",
            form_url="https://ecomtest.sberbank.ru/pp/x",
        )
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": "sync1",
            "currency": "643",
        }
        updated = sync_payment_from_bank(payment, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)

    def test_sync_idempotent_when_already_paid(self):
        order, _, _ = _order(status=Order.STATUS_CONFIRMED)
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="idem1",
            sber_order_id="55555555-5555-5555-5555-555555555555",
            paid_at=timezone.now(),
        )
        mock_client = MagicMock()
        sync_payment_from_bank(payment, client=mock_client)
        mock_client.get_order_status.assert_not_called()

    def test_callback_triggers_status_check(self):
        order, _, _ = _order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="cb1",
            sber_order_id="66666666-6666-6666-6666-666666666666",
            form_url="https://ecomtest.sberbank.ru/pp/x",
        )
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        handle_sber_callback(
            {
                "mdOrder": payment.sber_order_id,
                "orderNumber": payment.merchant_order_number,
                "operation": "deposited",
                "status": 1,
            },
            client=mock_client,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        self.assertIsNotNone(payment.callback_received_at)

    def test_amount_mismatch_fails(self):
        order, _, _ = _order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_REGISTERED,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="mm1",
            sber_order_id="77777777-7777-7777-7777-777777777777",
            form_url="https://ecomtest.sberbank.ru/pp/x",
        )
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 1,  # mismatch
        }
        updated = sync_payment_from_bank(payment, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_FAILED)

    def test_expire_unpaid_releases_stock(self):
        order, product, store = _order()
        stock = Stock.objects.get(product=product, store=store)
        stock.reserved_quantity = 1
        stock.save()
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        result = expire_unpaid_online_orders()
        self.assertEqual(result["cancelled"], 1)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 0)

    def test_expire_skips_paid(self):
        order, _, _ = _order()
        Payment.objects.create(
            order=order,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="expay",
            paid_at=timezone.now(),
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=60)
        )
        result = expire_unpaid_online_orders()
        self.assertEqual(result["cancelled"], 0)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_expire_rescues_paid_in_bank(self):
        order, _, _ = _order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="rescue1",
            sber_order_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            form_url="https://ecomtest.sberbank.ru/pp/x",
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=60)
        )
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        result = expire_unpaid_online_orders(client=mock_client)
        self.assertEqual(result["cancelled"], 0)
        self.assertGreaterEqual(result["rescued_paid"], 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)

    def test_sync_reversed_status(self):
        order, _, _ = _order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="rev1",
            sber_order_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            form_url="https://ecomtest.sberbank.ru/pp/x",
        )
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 3,
            "actionCode": 0,
            "amount": 100000,
        }
        updated = sync_payment_from_bank(payment, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_REVERSED)

    def test_late_policy_manual(self):
        order, _, _ = _order(status=Order.STATUS_CANCELLED)
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_NEEDS_REVIEW,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="late1",
            sber_order_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        )
        with override_settings(LATE_ONLINE_PAYMENT_POLICY="manual"):
            updated = apply_late_payment_policy(payment.pk, client=MagicMock())
        self.assertEqual(updated.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertIn("ручная сверка", updated.error_message)

    def test_late_policy_reverse(self):
        order, _, _ = _order(status=Order.STATUS_CANCELLED)
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_NEEDS_REVIEW,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="late2",
            sber_order_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
        )
        mock_client = MagicMock()
        mock_client.reverse_order.return_value = {"errorCode": "0"}
        with override_settings(LATE_ONLINE_PAYMENT_POLICY="reverse"):
            updated = apply_late_payment_policy(payment.pk, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_REVERSED)
        mock_client.reverse_order.assert_called_once()

    def test_late_policy_revive(self):
        order, product, store = _order(status=Order.STATUS_CANCELLED)
        stock = Stock.objects.get(product=product, store=store)
        stock.reserved_quantity = 0
        stock.save()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_NEEDS_REVIEW,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="late3",
            sber_order_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        )
        with override_settings(LATE_ONLINE_PAYMENT_POLICY="revive"):
            updated = apply_late_payment_policy(payment.pk, client=MagicMock())
        self.assertEqual(updated.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)

    def test_reconcile_and_hung_monitor(self):
        order, _, _ = _order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="rec1",
            sber_order_id="ffffffff-ffff-ffff-ffff-ffffffffffff",
            form_url="https://ecomtest.sberbank.ru/pp/x",
        )
        Payment.objects.filter(pk=payment.pk).update(
            created_at=timezone.now() - timedelta(minutes=10)
        )
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        result = reconcile_open_payments(
            client=mock_client, older_than_minutes=2, limit=50
        )
        self.assertEqual(result["synced"], 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)

        Payment.objects.create(
            order=order,
            status=Payment.STATUS_NEEDS_REVIEW,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="hung1",
            error_message="test review",
        )
        snap = find_hung_payments(pending_minutes=30)
        self.assertGreaterEqual(snap["needs_review_count"], 1)

    def test_register_http_outside_long_txn_marks_failed(self):
        order, _, _ = _order()
        mock_client = MagicMock()
        mock_client.register_order.side_effect = SberEcomError(
            "fail", error_code="7", payload={"errorCode": "7"}
        )
        with self.assertRaises(PaymentError):
            initiate_sber_payment(order, client=mock_client)
        payment = Payment.objects.filter(order=order).latest("created_at")
        self.assertEqual(payment.status, Payment.STATUS_FAILED)


@override_settings(
    SBER_ECOM_ENABLED=True,
    FRONTEND_URL="https://shop.test",
)
class PaymentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_pay_endpoint_wires_to_service(self):
        """View → initiate_sber_payment → клиент (мок HTTP, не мок всего сервиса)."""
        order, _, _ = _order()
        mock_client = MagicMock()
        mock_client.register_order.return_value = {
            "orderId": "88888888-8888-8888-8888-888888888888",
            "formUrl": "https://ecomtest.sberbank.ru/pp/pay",
            "raw": {"errorCode": "0"},
        }
        with patch(
            "apps.payments.services.SberEcomClient", return_value=mock_client
        ):
            resp = self.client.post(
                f"/api/v1/orders/{order.id}/pay/",
                {"phone": "79001112233"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["form_url"], mock_client.register_order.return_value["formUrl"])
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.status, Payment.STATUS_REGISTERED)
        self.assertEqual(payment.amount_kopecks, 100000)
        mock_client.register_order.assert_called_once()
        self.assertEqual(
            mock_client.register_order.call_args.kwargs["amount_kopecks"], 100000
        )

    def test_callback_endpoint_wires_to_sync(self):
        """Callback view вызывает реальный handle → sync с мок-клиентом банка."""
        order, _, _ = _order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="apicb",
            sber_order_id="99999999-9999-9999-9999-999999999999",
            form_url="https://ecomtest.sberbank.ru/pp/x",
        )
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        with patch(
            "apps.payments.services.SberEcomClient", return_value=mock_client
        ):
            resp = self.client.post(
                "/api/v1/payments/sber/callback/",
                {
                    "mdOrder": payment.sber_order_id,
                    "orderNumber": payment.merchant_order_number,
                    "operation": "deposited",
                    "status": 1,
                },
                format="json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertNotIn("found", resp.data)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        mock_client.get_order_status.assert_called()

    def test_callback_unknown_mdorder_still_200_no_oracle(self):
        resp = self.client.post(
            "/api/v1/payments/sber/callback/",
            {
                "mdOrder": "00000000-0000-0000-0000-000000000000",
                "operation": "deposited",
                "status": 1,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertNotIn("found", resp.data)


class PaymentMigrationFileTests(TestCase):
    def test_initial_migration_lists_needs_review(self):
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[1]
            / "apps"
            / "payments"
            / "migrations"
            / "0001_initial.py"
        )
        text = path.read_text(encoding="utf-8")
        self.assertIn("needs_review", text)
        self.assertIn("orders", text)
        self.assertIn("0006_order_anonymized_at", text)
