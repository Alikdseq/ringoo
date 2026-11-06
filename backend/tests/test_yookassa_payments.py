"""Тесты ЮKassa (только моки HTTP, без реального API)."""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import PaymentError, initiate_online_payment
from apps.payments.yookassa_service import (
    handle_yookassa_webhook,
    initiate_yookassa_payment,
    sync_payment_from_yookassa,
)
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from integrations.yookassa.client import YooKassaClient, YooKassaError


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
    return order


def _yk_payment_response(
    *,
    payment_id="yk-pay-1",
    status="pending",
    amount="1000.00",
    currency="RUB",
    order_id=None,
    local_payment_id=None,
    confirmation_url="https://yoomoney.ru/checkout/payments/v2/contract?orderId=yk-pay-1",
    test=True,
):
    return {
        "id": payment_id,
        "status": status,
        "amount": {"value": amount, "currency": currency},
        "confirmation": {"type": "redirect", "confirmation_url": confirmation_url},
        "paid": status == "succeeded",
        "test": test,
        "metadata": {
            "order_id": str(order_id or ""),
            "payment_id": str(local_payment_id or ""),
            "order_number": "R-1",
        },
    }


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    YOOKASSA_API_URL="https://api.yookassa.ru/v3",
    SBER_ECOM_ENABLED=False,
    FRONTEND_URL="https://shop.test",
)
class YooKassaClientTests(TestCase):
    def test_disabled_raises(self):
        client = YooKassaClient(enabled=False, shop_id="s", secret_key="test_x")
        with self.assertRaises(YooKassaError):
            client.create_payment(
                amount="10.00",
                return_url="https://shop.test/ok",
                description="x",
                metadata={},
                idempotence_key="k1",
            )

    def test_misconfigured_without_shop(self):
        with self.assertRaises(YooKassaError) as ctx:
            YooKassaClient(
                enabled=True,
                shop_id="",
                secret_key="test_abc",
                test_mode=True,
            )
        self.assertEqual(ctx.exception.code, "yookassa_misconfigured")

    def test_test_mode_rejects_live_key(self):
        with self.assertRaises(YooKassaError) as ctx:
            YooKassaClient(
                enabled=True,
                shop_id="1",
                secret_key="live_abc",
                test_mode=True,
            )
        self.assertEqual(ctx.exception.code, "yookassa_test_key_required")

    def test_create_payment_sends_basic_auth_amount_and_idempotence(self):
        captured = {}

        def fake_urlopen(req, timeout=None, context=None):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["auth"] = req.headers.get("Authorization") or req.get_header(
                "Authorization"
            )
            captured["idem"] = req.headers.get("Idempotence-Key") or req.get_header(
                "Idempotence-key"
            )
            body = json.loads(req.data.decode("utf-8"))
            captured["body"] = body

            class Resp:
                status = 200

                def read(self):
                    return json.dumps(
                        _yk_payment_response(local_payment_id="p1", order_id="o1")
                    ).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

            return Resp()

        client = YooKassaClient(
            enabled=True,
            shop_id="shop-test",
            secret_key="test_secret_key_value",
            test_mode=True,
        )
        with patch("integrations.yookassa.client.request.urlopen", side_effect=fake_urlopen):
            data = client.create_payment(
                amount=Decimal("1000.00"),
                return_url="https://shop.test/orders/1/payment/return",
                description="Заказ X",
                metadata={"order_id": "o1"},
                idempotence_key="idem-123",
            )
        self.assertEqual(captured["method"], "POST")
        self.assertIn("/payments", captured["url"])
        self.assertTrue(str(captured["auth"]).startswith("Basic "))
        self.assertEqual(captured["idem"], "idem-123")
        self.assertEqual(captured["body"]["amount"]["value"], "1000.00")
        self.assertEqual(captured["body"]["amount"]["currency"], "RUB")
        self.assertEqual(captured["body"]["confirmation"]["type"], "redirect")
        self.assertTrue(captured["body"]["capture"])
        self.assertEqual(data["id"], "yk-pay-1")


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    YOOKASSA_API_URL="https://api.yookassa.ru/v3",
    SBER_ECOM_ENABLED=False,
    FRONTEND_URL="https://shop.test",
)
class YooKassaServiceTests(TestCase):
    def test_disabled_config(self):
        order = _order()
        with override_settings(YOOKASSA_ENABLED=False, SBER_ECOM_ENABLED=False):
            with self.assertRaises(PaymentError) as ctx:
                initiate_online_payment(order)
            self.assertEqual(ctx.exception.code, "payments_disabled")

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_initiate_stores_payment_and_url(self, MockClient):
        order = _order()
        api = MockClient.return_value

        def create_payment(**kwargs):
            # payment row already exists
            p = Payment.objects.filter(order=order).latest("created_at")
            return _yk_payment_response(
                order_id=order.id,
                local_payment_id=p.id,
                amount="1000.00",
            )

        api.create_payment.side_effect = create_payment
        result = initiate_yookassa_payment(order, client=api)
        self.assertFalse(result.reused)
        self.assertTrue(result.form_url.startswith("https://"))
        payment = result.payment
        self.assertEqual(payment.provider, Payment.PROVIDER_YOOKASSA)
        self.assertEqual(payment.yookassa_payment_id, "yk-pay-1")
        self.assertEqual(payment.status, Payment.STATUS_REGISTERED)
        self.assertEqual(payment.currency, "RUB")
        self.assertTrue(payment.is_test)
        # сумма из заказа, не из клиента
        self.assertEqual(payment.amount, Decimal("1000.00"))
        call_kwargs = api.create_payment.call_args.kwargs
        self.assertEqual(str(call_kwargs["idempotence_key"]), str(payment.id))
        self.assertEqual(call_kwargs["amount"], payment.amount)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_reuse_active_payment(self, MockClient):
        order = _order()
        api = MockClient.return_value

        def create_payment(**kwargs):
            p = Payment.objects.filter(order=order).latest("created_at")
            return _yk_payment_response(order_id=order.id, local_payment_id=p.id)

        def get_payment(yk_id):
            p = Payment.objects.filter(order=order).latest("created_at")
            return _yk_payment_response(
                payment_id=p.yookassa_payment_id or yk_id,
                status="pending",
                order_id=order.id,
                local_payment_id=p.id,
            )

        api.create_payment.side_effect = create_payment
        api.get_payment.side_effect = get_payment
        first = initiate_yookassa_payment(order, client=api)
        second = initiate_yookassa_payment(order, client=api)
        self.assertTrue(second.reused)
        self.assertEqual(first.payment.id, second.payment.id)
        self.assertEqual(api.create_payment.call_count, 1)
        self.assertGreaterEqual(api.get_payment.call_count, 1)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_api_error_marks_failed(self, MockClient):
        order = _order()
        api = MockClient.return_value
        api.create_payment.side_effect = YooKassaError(
            "fail", code="yookassa_http_error", payload={"code": "invalid_request"}
        )
        with self.assertRaises(PaymentError) as ctx:
            initiate_yookassa_payment(order, client=api)
        self.assertEqual(ctx.exception.code, "yookassa_create_failed")
        p = Payment.objects.filter(order=order).latest("created_at")
        self.assertEqual(p.status, Payment.STATUS_FAILED)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_sync_succeeded_marks_paid(self, MockClient):
        order = _order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number=str(order.id).replace("-", "")[:32],
            yookassa_payment_id="yk-pay-1",
            form_url="https://pay.example/x",
            is_test=True,
        )
        api = MockClient.return_value
        api.get_payment.return_value = _yk_payment_response(
            status="succeeded",
            order_id=order.id,
            local_payment_id=payment.id,
            amount="1000.00",
        )
        updated = sync_payment_from_yookassa(payment, client=api)
        self.assertEqual(updated.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_sync_amount_mismatch(self, MockClient):
        order = _order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="a" * 32,
            yookassa_payment_id="yk-pay-1",
            form_url="https://pay.example/x",
        )
        api = MockClient.return_value
        api.get_payment.return_value = _yk_payment_response(
            status="succeeded",
            order_id=order.id,
            local_payment_id=payment.id,
            amount="1.00",
        )
        updated = sync_payment_from_yookassa(payment, client=api)
        self.assertEqual(updated.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertIn("Сумма", updated.error_message)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_sync_currency_mismatch(self, MockClient):
        order = _order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="b" * 32,
            yookassa_payment_id="yk-pay-2",
            form_url="https://pay.example/x",
        )
        api = MockClient.return_value
        api.get_payment.return_value = _yk_payment_response(
            status="succeeded",
            order_id=order.id,
            local_payment_id=payment.id,
            currency="USD",
        )
        updated = sync_payment_from_yookassa(payment, client=api)
        self.assertEqual(updated.status, Payment.STATUS_NEEDS_REVIEW)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_sync_wrong_payment_id(self, MockClient):
        order = _order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="c" * 32,
            yookassa_payment_id="yk-pay-local",
            form_url="https://pay.example/x",
        )
        api = MockClient.return_value
        resp = _yk_payment_response(
            payment_id="yk-other",
            status="succeeded",
            order_id=order.id,
            local_payment_id=payment.id,
        )
        api.get_payment.return_value = resp
        updated = sync_payment_from_yookassa(payment, client=api)
        self.assertEqual(updated.status, Payment.STATUS_NEEDS_REVIEW)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_sync_canceled(self, MockClient):
        order = _order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="d" * 32,
            yookassa_payment_id="yk-pay-3",
            form_url="https://pay.example/x",
        )
        api = MockClient.return_value
        api.get_payment.return_value = _yk_payment_response(
            payment_id="yk-pay-3",
            status="canceled",
            order_id=order.id,
            local_payment_id=payment.id,
        )
        updated = sync_payment_from_yookassa(payment, client=api)
        self.assertEqual(updated.status, Payment.STATUS_FAILED)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_webhook_idempotent(self, MockClient):
        order = _order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="e" * 32,
            yookassa_payment_id="yk-pay-wh",
            form_url="https://pay.example/x",
        )
        api = MockClient.return_value
        api.get_payment.return_value = _yk_payment_response(
            payment_id="yk-pay-wh",
            status="succeeded",
            order_id=order.id,
            local_payment_id=payment.id,
        )
        payload = {
            "event": "payment.succeeded",
            "object": {"id": "yk-pay-wh", "status": "succeeded"},
        }
        first = handle_yookassa_webhook(payload, client=api)
        second = handle_yookassa_webhook(payload, client=api)
        self.assertEqual(first.status, Payment.STATUS_PAID)
        self.assertEqual(second.status, Payment.STATUS_PAID)
        self.assertEqual(Payment.objects.filter(order=order, status=Payment.STATUS_PAID).count(), 1)


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    SBER_ECOM_ENABLED=False,
    FRONTEND_URL="https://shop.test",
)
class YooKassaAPIViewTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_pay_endpoint_returns_confirmation_url(self, MockClient):
        from apps.orders.guest_access import issue_guest_access_token

        order = _order()
        guest_token = issue_guest_access_token(order)
        yk = MockClient.return_value

        def create_payment(**kwargs):
            p = Payment.objects.filter(order=order).latest("created_at")
            return _yk_payment_response(order_id=order.id, local_payment_id=p.id)

        yk.create_payment.side_effect = create_payment
        resp = self.api.post(
            f"/api/v1/orders/{order.id}/pay/",
            {
                "phone": order.phone,
                "order_number": order.order_number,
                "guest_token": guest_token,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("form_url", resp.data)
        self.assertIn("confirmation_url", resp.data)
        self.assertEqual(resp.data["form_url"], resp.data["confirmation_url"])
        self.assertEqual(resp.data["payment"]["provider"], "yookassa")

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_webhook_endpoint(self, MockClient):
        order = _order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="f" * 32,
            yookassa_payment_id="yk-wh-api",
            form_url="https://pay.example/x",
        )
        MockClient.return_value.get_payment.return_value = _yk_payment_response(
            payment_id="yk-wh-api",
            status="succeeded",
            order_id=order.id,
            local_payment_id=payment.id,
        )
        resp = self.api.post(
            "/api/v1/payments/yookassa/webhook/",
            {"event": "payment.succeeded", "object": {"id": "yk-wh-api", "status": "waiting_for_capture"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
