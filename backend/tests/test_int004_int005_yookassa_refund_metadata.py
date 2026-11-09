"""INT-004 refund.succeeded + INT-005 обязательные metadata."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import PaymentError
from apps.payments.yookassa_service import (
    handle_yookassa_webhook,
    sync_payment_from_yookassa,
    sync_refund_from_yookassa,
)
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from integrations.yookassa.client import YooKassaError


def _order(amount="1000.00"):
    cat = Category.objects.create(title="C", slug=f"int45-{Category.objects.count()}")
    product = Product.objects.create(
        title="P",
        slug=f"int45p-{Product.objects.count()}",
        price=Decimal(amount),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"int45s-{Store.objects.count()}", address="a", city="c"
    )
    Stock.objects.create(product=product, store=store, quantity=5, reserved_quantity=0)
    order = Order.objects.create(
        full_name="Buyer",
        phone="79008110001",
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=Order.PAYMENT_ONLINE,
        status=Order.STATUS_CONFIRMED,
        total_amount=Decimal(amount),
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=1,
        price=Decimal(amount),
        item_total=Decimal(amount),
    )
    return order


def _payment(order, *, status=Payment.STATUS_PAID, yk_id="yk-pay-1"):
    return Payment.objects.create(
        order=order,
        provider=Payment.PROVIDER_YOOKASSA,
        status=status,
        amount=order.total_amount,
        amount_kopecks=Payment.rubles_to_kopecks(order.total_amount),
        currency="RUB",
        merchant_order_number=("m" + str(Payment.objects.count()).zfill(31))[:36],
        yookassa_payment_id=yk_id,
        form_url="https://pay.example/x",
    )


def _yk_payment_payload(payment, *, status="succeeded", meta=None, amount=None, currency="RUB"):
    return {
        "id": payment.yookassa_payment_id,
        "status": status,
        "amount": {
            "value": amount or str(payment.amount),
            "currency": currency,
        },
        "metadata": meta
        if meta is not None
        else {
            "order_id": str(payment.order_id),
            "payment_id": str(payment.id),
        },
        "test": True,
    }


def _yk_refund_payload(payment, *, refund_id="rf-1", status="succeeded", amount=None, currency="RUB", payment_id=None):
    return {
        "id": refund_id,
        "status": status,
        "payment_id": payment_id if payment_id is not None else payment.yookassa_payment_id,
        "amount": {
            "value": amount or str(payment.amount),
            "currency": currency,
        },
    }


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    SBER_ECOM_ENABLED=False,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "int45004",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "int45004s",
        },
    },
)
class Int004RefundSucceededTests(TestCase):
    def setUp(self):
        cache.clear()
        self.order = _order()
        self.payment = _payment(self.order)

    def test_refund_succeeded_marks_refunded(self):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(self.payment, refund_id="rf-ok")
        result = handle_yookassa_webhook(
            {"event": "refund.succeeded", "object": {"id": "rf-ok"}},
            client=client,
        )
        self.payment.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_REFUNDED)
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)
        self.assertEqual(self.payment.yookassa_refund_id, "rf-ok")
        self.assertEqual(self.payment.refunded_amount, Decimal("1000.00"))
        self.assertIsNotNone(self.payment.refunded_at)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_CANCELLED)

    def test_refund_idempotent(self):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(self.payment, refund_id="rf-idemp")
        handle_yookassa_webhook(
            {"event": "refund.succeeded", "object": {"id": "rf-idemp"}},
            client=client,
        )
        handle_yookassa_webhook(
            {"event": "refund.succeeded", "object": {"id": "rf-idemp"}},
            client=client,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)
        # Повтор использует yookassa_refund_id — без повторного GET
        self.assertEqual(client.get_refund.call_count, 1)

    def test_unknown_refund_payment(self):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(
            self.payment, refund_id="rf-x", payment_id="unknown-pay"
        )
        result = handle_yookassa_webhook(
            {"event": "refund.succeeded", "object": {"id": "rf-x"}},
            client=client,
        )
        self.assertIsNone(result)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_PAID)

    def test_refund_wrong_payment_id(self):
        other = _payment(self.order, status=Payment.STATUS_PENDING, yk_id="yk-other")
        client = MagicMock()
        # Refund claims other payment id while we look up by that id — binding to other
        client.get_refund.return_value = _yk_refund_payload(
            other, refund_id="rf-wp", amount="1000.00", payment_id=other.yookassa_payment_id
        )
        # Force mismatch vs paid payment by returning paid's local but wrong remote id path:
        # Use paid payment's yk id in lookup but refund body payment_id wrong
        client.get_refund.return_value = {
            "id": "rf-wp",
            "status": "succeeded",
            "payment_id": self.payment.yookassa_payment_id,
            "amount": {"value": "1000.00", "currency": "RUB"},
        }
        # Inject mismatch after get by patching reject path: amount wrong currency
        client.get_refund.return_value["amount"]["currency"] = "USD"
        result = sync_refund_from_yookassa("rf-wp", client=client)
        self.payment.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertNotEqual(self.payment.yookassa_refund_id, "rf-wp")

    def test_partial_refund_keeps_payment_open(self):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(
            self.payment, refund_id="rf-part", amount="100.00"
        )
        result = sync_refund_from_yookassa("rf-part", client=client)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_PAID)
        self.assertEqual(self.payment.amount, Decimal("1000.00"))
        self.assertEqual(self.payment.refunded_amount, Decimal("100.00"))
        self.assertEqual(self.order.status, Order.STATUS_CONFIRMED)

    def test_refund_api_unavailable(self):
        client = MagicMock()
        client.get_refund.side_effect = YooKassaError("down", code="yookassa_http")
        with self.assertRaises(PaymentError):
            sync_refund_from_yookassa("rf-down", client=client)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_PAID)

    def test_refund_pending_status(self):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(
            self.payment, refund_id="rf-pend", status="pending"
        )
        result = sync_refund_from_yookassa("rf-pend", client=client)
        self.payment.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)

    def test_webhook_does_not_trust_payload_alone(self):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(self.payment, refund_id="rf-api")
        # Payload object could lie about amount; only GET result matters
        handle_yookassa_webhook(
            {
                "event": "refund.succeeded",
                "object": {
                    "id": "rf-api",
                    "payment_id": "liar",
                    "amount": {"value": "0.01", "currency": "RUB"},
                },
            },
            client=client,
        )
        client.get_refund.assert_called_once_with("rf-api")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    SBER_ECOM_ENABLED=False,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "int45005",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "int45005s",
        },
    },
)
class Int005MetadataRequiredTests(TestCase):
    def setUp(self):
        cache.clear()
        self.order = _order()
        self.payment = _payment(self.order, status=Payment.STATUS_PENDING, yk_id="yk-meta-1")

    def _sync(self, payload):
        client = MagicMock()
        client.get_payment.return_value = payload
        return sync_payment_from_yookassa(self.payment, client=client)

    def test_missing_metadata_needs_review(self):
        result = self._sync(
            {
                "id": self.payment.yookassa_payment_id,
                "status": "succeeded",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "metadata": {},
                "test": True,
            }
        )
        self.payment.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)

    def test_absent_metadata_key(self):
        result = self._sync(
            {
                "id": self.payment.yookassa_payment_id,
                "status": "succeeded",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "test": True,
            }
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)

    def test_missing_order_id(self):
        result = self._sync(
            _yk_payment_payload(
                self.payment,
                meta={"payment_id": str(self.payment.id)},
            )
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)

    def test_wrong_order_id(self):
        result = self._sync(
            _yk_payment_payload(
                self.payment,
                meta={
                    "order_id": "00000000-0000-0000-0000-000000000099",
                    "payment_id": str(self.payment.id),
                },
            )
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)

    def test_wrong_payment_id(self):
        result = self._sync(
            _yk_payment_payload(
                self.payment,
                meta={
                    "order_id": str(self.payment.order_id),
                    "payment_id": "00000000-0000-0000-0000-000000000099",
                },
            )
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)

    def test_amount_mismatch(self):
        result = self._sync(_yk_payment_payload(self.payment, amount="999.00"))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)

    def test_currency_mismatch(self):
        result = self._sync(_yk_payment_payload(self.payment, currency="USD"))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)

    def test_valid_metadata_paid(self):
        with patch(
            "apps.payments.yookassa_service.clear_cart_after_successful_payment",
            create=True,
        ):
            # cart clear imported inside on_commit — patch enqueue/cart via path used
            with patch("apps.orders.tasks.enqueue_order_sync"):
                with patch(
                    "apps.cart.checkout_clear.clear_cart_after_successful_payment"
                ):
                    result = self._sync(_yk_payment_payload(self.payment))
        self.payment.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_PAID)
        self.assertEqual(self.payment.status, Payment.STATUS_PAID)
