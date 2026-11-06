"""FUNC-001: expire_unpaid сверяет ЮKassa перед отменой."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import PaymentError, expire_unpaid_online_orders
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store


def _online_order(*, minutes_ago=60):
    cat = Category.objects.create(title="C", slug=f"f1-{Category.objects.count()}")
    product = Product.objects.create(
        title="P",
        slug=f"f1p-{Product.objects.count()}",
        price=Decimal("1000.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"f1s-{Store.objects.count()}", address="a", city="c"
    )
    Stock.objects.create(
        product=product, store=store, quantity=5, reserved_quantity=1
    )
    order = Order.objects.create(
        full_name="Buyer",
        phone="79001110001",
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
    Order.objects.filter(pk=order.pk).update(
        created_at=timezone.now() - timedelta(minutes=minutes_ago)
    )
    order.refresh_from_db()
    return order, product, store


def _yk_payment(order, *, yk_id="yk-expire-1"):
    return Payment.objects.create(
        order=order,
        provider=Payment.PROVIDER_YOOKASSA,
        status=Payment.STATUS_PENDING,
        amount=order.total_amount,
        amount_kopecks=100000,
        currency="RUB",
        merchant_order_number="e" * 32,
        yookassa_payment_id=yk_id,
        form_url="https://yookassa.test/pay",
    )


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop",
    YOOKASSA_SECRET_KEY="secret",
    SBER_ECOM_ENABLED=False,
    ONLINE_PAYMENT_TIMEOUT_MINUTES=20,
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class Func001ExpireYooKassaSyncTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_remote_succeeded_does_not_cancel(self, MockClient):
        order, product, store = _online_order()
        payment = _yk_payment(order)
        MockClient.return_value.get_payment.return_value = {
            "id": payment.yookassa_payment_id,
            "status": "succeeded",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "metadata": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
        }
        result = expire_unpaid_online_orders()
        self.assertEqual(result["cancelled"], 0)
        self.assertGreaterEqual(result["rescued_paid"], 1)
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertNotEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 1)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_remote_pending_expires_after_timeout(self, MockClient):
        order, product, store = _online_order()
        payment = _yk_payment(order, yk_id="yk-pend")
        MockClient.return_value.get_payment.return_value = {
            "id": "yk-pend",
            "status": "pending",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "metadata": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
        }
        result = expire_unpaid_online_orders()
        self.assertEqual(result["cancelled"], 1)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 0)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_remote_canceled_expires(self, MockClient):
        order, _, _ = _online_order()
        payment = _yk_payment(order, yk_id="yk-can")
        MockClient.return_value.get_payment.return_value = {
            "id": "yk-can",
            "status": "canceled",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "metadata": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
        }
        result = expire_unpaid_online_orders()
        self.assertEqual(result["cancelled"], 1)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_api_unavailable_does_not_blind_cancel(self, MockClient):
        order, product, store = _online_order()
        _yk_payment(order, yk_id="yk-down")
        MockClient.return_value.get_payment.side_effect = RuntimeError("down")
        result = expire_unpaid_online_orders()
        self.assertEqual(result["cancelled"], 0)
        self.assertGreaterEqual(result["skipped_uncertain"], 1)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 1)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_wrong_amount_does_not_mark_paid_then_may_expire(self, MockClient):
        order, _, _ = _online_order()
        payment = _yk_payment(order, yk_id="yk-amt")
        MockClient.return_value.get_payment.return_value = {
            "id": "yk-amt",
            "status": "succeeded",
            "amount": {"value": "1.00", "currency": "RUB"},
            "metadata": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
        }
        # INT-005: неверная сумма → needs_review; expire не отменяет (возможна оплата)
        result = expire_unpaid_online_orders()
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_NEEDS_REVIEW)
        order.refresh_from_db()
        self.assertNotEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(result["cancelled"], 0)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_repeat_expire_idempotent(self, MockClient):
        order, product, store = _online_order()
        payment = _yk_payment(order, yk_id="yk-idemp")
        MockClient.return_value.get_payment.return_value = {
            "id": "yk-idemp",
            "status": "pending",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "metadata": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
        }
        r1 = expire_unpaid_online_orders()
        r2 = expire_unpaid_online_orders()
        self.assertEqual(r1["cancelled"], 1)
        self.assertEqual(r2["cancelled"], 0)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 0)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_recover_after_api_error_then_rescue(self, MockClient):
        order, product, store = _online_order()
        payment = _yk_payment(order, yk_id="yk-retry")
        MockClient.return_value.get_payment.side_effect = [
            RuntimeError("down"),
            {
                "id": "yk-retry",
                "status": "succeeded",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "metadata": {
                    "order_id": str(order.id),
                    "payment_id": str(payment.id),
                },
            },
        ]
        r1 = expire_unpaid_online_orders()
        self.assertEqual(r1["cancelled"], 0)
        r2 = expire_unpaid_online_orders()
        self.assertEqual(r2["cancelled"], 0)
        self.assertGreaterEqual(r2["rescued_paid"], 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 1)
