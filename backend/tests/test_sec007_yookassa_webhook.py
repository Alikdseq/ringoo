"""SEC-007: hardening webhook ЮKassa без ослабления re-fetch."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.yookassa_service import handle_yookassa_webhook
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store


def _order():
    cat = Category.objects.create(title="C", slug=f"yk7-{Category.objects.count()}")
    product = Product.objects.create(
        title="P",
        slug=f"yk7p-{Product.objects.count()}",
        price=Decimal("1000.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"yk7s-{Store.objects.count()}", address="a", city="c"
    )
    Stock.objects.create(product=product, store=store, quantity=5, reserved_quantity=0)
    order = Order.objects.create(
        full_name="Buyer",
        phone="79007110001",
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=Order.PAYMENT_ONLINE,
        status=Order.STATUS_NEW,
        total_amount=Decimal("1000.00"),
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=1,
        price=Decimal("1000.00"),
        item_total=Decimal("1000.00"),
    )
    return order


def _yk_ok(payment: Payment, *, status="succeeded", amount="1000.00", currency="RUB"):
    return {
        "id": payment.yookassa_payment_id,
        "status": status,
        "amount": {"value": amount, "currency": currency},
        "metadata": {
            "order_id": str(payment.order_id),
            "payment_id": str(payment.id),
        },
        "test": True,
    }


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    SBER_ECOM_ENABLED=False,
    YOOKASSA_WEBHOOK_MAX_BODY_BYTES=4096,
    YOOKASSA_WEBHOOK_SYNC_DEBOUNCE_SECONDS=2,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec007",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec007s",
        },
    },
)
class Sec007YooKassaWebhookTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def _pending_payment(self, order, yk_id="yk-sec7-1"):
        return Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="g" * 32,
            yookassa_payment_id=yk_id,
            form_url="https://pay.example/x",
        )

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_forged_succeeded_without_api_does_not_pay(self, MockClient):
        """Webhook object.status=succeeded без успешного API — не PAID."""
        order = _order()
        payment = self._pending_payment(order)
        MockClient.return_value.get_payment.side_effect = Exception("unreachable")
        # PaymentError path — sync raises
        from integrations.yookassa.client import YooKassaError

        MockClient.return_value.get_payment.side_effect = YooKassaError("down")
        handle_yookassa_webhook(
            {
                "event": "payment.succeeded",
                "object": {"id": payment.yookassa_payment_id, "status": "succeeded"},
            },
            client=MockClient.return_value,
        )
        payment.refresh_from_db()
        self.assertNotEqual(payment.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertNotEqual(order.status, Order.STATUS_CONFIRMED)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_wrong_amount_rejected(self, MockClient):
        order = _order()
        payment = self._pending_payment(order)
        MockClient.return_value.get_payment.return_value = _yk_ok(
            payment, amount="1.00"
        )
        handle_yookassa_webhook(
            {
                "event": "payment.succeeded",
                "object": {"id": payment.yookassa_payment_id},
            },
            client=MockClient.return_value,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_NEEDS_REVIEW)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_wrong_currency_rejected(self, MockClient):
        order = _order()
        payment = self._pending_payment(order, yk_id="yk-cur")
        MockClient.return_value.get_payment.return_value = _yk_ok(
            payment, currency="USD"
        )
        handle_yookassa_webhook(
            {"event": "payment.succeeded", "object": {"id": "yk-cur"}},
            client=MockClient.return_value,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_NEEDS_REVIEW)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_wrong_metadata_rejected(self, MockClient):
        order = _order()
        payment = self._pending_payment(order, yk_id="yk-meta")
        data = _yk_ok(payment)
        data["metadata"]["order_id"] = "00000000-0000-0000-0000-000000000099"
        MockClient.return_value.get_payment.return_value = data
        handle_yookassa_webhook(
            {"event": "payment.succeeded", "object": {"id": "yk-meta"}},
            client=MockClient.return_value,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_NEEDS_REVIEW)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_unknown_payment_id_noop(self, MockClient):
        result = handle_yookassa_webhook(
            {
                "event": "payment.succeeded",
                "object": {"id": "yk-unknown-xyz"},
            },
            client=MockClient.return_value,
        )
        self.assertIsNone(result)
        MockClient.return_value.get_payment.assert_not_called()

    def test_invalid_payload_structure(self):
        resp = self.api.post(
            "/api/v1/payments/yookassa/webhook/",
            ["not", "a", "dict"],
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_oversized_payload_rejected(self):
        huge = {"event": "payment.succeeded", "object": {"id": "x", "pad": "Z" * 8000}}
        resp = self.api.post(
            "/api/v1/payments/yookassa/webhook/",
            huge,
            format="json",
        )
        self.assertEqual(resp.status_code, 413)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_ignored_event_no_api_call(self, MockClient):
        order = _order()
        payment = self._pending_payment(order, yk_id="yk-ign")
        handle_yookassa_webhook(
            {"event": "payment.waiting_for_something_else", "object": {"id": "yk-ign"}},
            client=MockClient.return_value,
        )
        MockClient.return_value.get_payment.assert_not_called()
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PENDING)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_valid_webhook_pays_once(self, MockClient):
        order = _order()
        payment = self._pending_payment(order, yk_id="yk-ok")
        MockClient.return_value.get_payment.return_value = _yk_ok(payment)
        first = handle_yookassa_webhook(
            {"event": "payment.succeeded", "object": {"id": "yk-ok"}},
            client=MockClient.return_value,
        )
        second = handle_yookassa_webhook(
            {"event": "payment.succeeded", "object": {"id": "yk-ok"}},
            client=MockClient.return_value,
        )
        self.assertEqual(first.status, Payment.STATUS_PAID)
        self.assertEqual(second.status, Payment.STATUS_PAID)
        # debounce: второй вызов может не ходить в API
        self.assertGreaterEqual(MockClient.return_value.get_payment.call_count, 1)
        self.assertLessEqual(MockClient.return_value.get_payment.call_count, 2)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_api_unavailable_does_not_mark_paid(self, MockClient):
        order = _order()
        payment = self._pending_payment(order, yk_id="yk-down")
        MockClient.return_value.get_payment.side_effect = RuntimeError("yk down")
        result = handle_yookassa_webhook(
            {"event": "payment.succeeded", "object": {"id": "yk-down"}},
            client=MockClient.return_value,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PENDING)
        # handler may return payment object even if sync failed
        if result is not None:
            self.assertEqual(result.status, Payment.STATUS_PENDING)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_api_recovers_after_failure_then_pays(self, MockClient):
        order = _order()
        payment = self._pending_payment(order, yk_id="yk-retry")
        MockClient.return_value.get_payment.side_effect = [
            RuntimeError("yk down"),
            _yk_ok(payment),
        ]
        handle_yookassa_webhook(
            {"event": "payment.succeeded", "object": {"id": "yk-retry"}},
            client=MockClient.return_value,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PENDING)
        cache.clear()  # сброс debounce после ошибки
        handle_yookassa_webhook(
            {"event": "payment.succeeded", "object": {"id": "yk-retry"}},
            client=MockClient.return_value,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_repeated_webhooks_remain_single_paid(self, MockClient):
        """Идемпотентность повторных webhook (без потоков: SQLite lock в тестах)."""
        order = _order()
        payment = self._pending_payment(order, yk_id="yk-race")
        MockClient.return_value.get_payment.return_value = _yk_ok(payment)
        payload = {"event": "payment.succeeded", "object": {"id": "yk-race"}}
        for _ in range(5):
            handle_yookassa_webhook(payload, client=MockClient.return_value)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        # Не больше одного реального get_payment при debounce (первый + возможно без debounce)
        self.assertLessEqual(MockClient.return_value.get_payment.call_count, 2)
