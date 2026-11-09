"""INV-002: полный и частичный возврат ЮKassa без увеличения остатка."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentRefund
from apps.payments.services import PaymentError
from apps.payments.yookassa_service import (
    handle_yookassa_webhook,
    sync_refund_from_yookassa,
)
from apps.stores.models import Stock
from integrations.yookassa.client import YooKassaError
from tests.test_int004_int005_yookassa_refund_metadata import (
    _order,
    _payment,
    _yk_refund_payload,
)


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    SBER_ECOM_ENABLED=False,
    RETURNS_ENABLED=False,
)
class FullAndPartialRefundTests(TestCase):
    def setUp(self):
        self.order = _order()
        self.payment = _payment(self.order)
        self.stock = Stock.objects.get(store=self.order.store)
        self.stock.quantity = 5
        self.stock.reserved_quantity = 1
        self.stock.save(update_fields=["quantity", "reserved_quantity"])

    def _refund(self, refund_id, amount, *, status="succeeded"):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(
            self.payment, refund_id=refund_id, amount=amount, status=status
        )
        return client

    def test_full_refund_cancels_unshipped_order_and_releases_reserve_once(self):
        client = self._refund("rf-full", "1000.00")
        handle_yookassa_webhook(
            {"event": "refund.succeeded", "object": {"id": "rf-full", "status": "succeeded"}},
            client=client,
        )
        handle_yookassa_webhook(
            {"event": "refund.succeeded", "object": {"id": "rf-full", "status": "succeeded"}},
            client=client,
        )
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)
        self.assertEqual(self.payment.amount, Decimal("1000.00"))
        self.assertEqual(self.payment.refunded_amount, Decimal("1000.00"))
        self.assertEqual(self.order.status, Order.STATUS_CANCELLED)
        self.assertEqual(self.stock.reserved_quantity, 0)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(PaymentRefund.objects.filter(payment=self.payment).count(), 1)
        self.assertEqual(client.get_refund.call_count, 1)

    def test_two_partials_then_stop_at_paid_amount(self):
        sync_refund_from_yookassa("rf-a", client=self._refund("rf-a", "400.00"))
        sync_refund_from_yookassa("rf-b", client=self._refund("rf-b", "600.00"))
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)
        self.assertEqual(self.payment.amount, Decimal("1000.00"))
        self.assertEqual(self.payment.refunded_amount, Decimal("1000.00"))
        self.assertEqual(self.order.status, Order.STATUS_CANCELLED)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 0)
        third = sync_refund_from_yookassa("rf-c", client=self._refund("rf-c", "1.00"))
        self.payment.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(third.status, Payment.STATUS_REFUNDED)
        self.assertEqual(self.payment.refunded_amount, Decimal("1000.00"))
        self.assertEqual(PaymentRefund.objects.count(), 2)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 0)

    def test_partial_does_not_move_stock_or_order(self):
        sync_refund_from_yookassa("rf-p", client=self._refund("rf-p", "250.00"))
        sync_refund_from_yookassa("rf-p", client=self._refund("rf-p", "250.00"))
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_PAID)
        self.assertEqual(self.payment.amount, Decimal("1000.00"))
        self.assertEqual(self.payment.refunded_amount, Decimal("250.00"))
        self.assertEqual(self.order.status, Order.STATUS_CONFIRMED)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 1)
        self.assertEqual(PaymentRefund.objects.count(), 1)

    def test_amount_above_paid_is_rejected(self):
        sync_refund_from_yookassa("rf-over", client=self._refund("rf-over", "1000.01"))
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertEqual(self.payment.amount, Decimal("1000.00"))
        self.assertIsNone(self.payment.refunded_amount)
        self.assertEqual(self.order.status, Order.STATUS_CONFIRMED)
        self.assertEqual(self.stock.reserved_quantity, 1)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(PaymentRefund.objects.count(), 0)

    def test_completed_order_refund_does_not_restock(self):
        self.order.status = Order.STATUS_COMPLETED
        self.order.save(update_fields=["status"])
        sync_refund_from_yookassa("rf-done", client=self._refund("rf-done", "1000.00"))
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)
        self.assertEqual(self.order.status, Order.STATUS_COMPLETED)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 1)

    def test_provider_error_changes_nothing(self):
        client = MagicMock()
        client.get_refund.side_effect = YooKassaError("down", code="yookassa_unreachable")
        with self.assertRaises(PaymentError):
            sync_refund_from_yookassa("rf-down", client=client)
        self.payment.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_PAID)
        self.assertEqual(self.stock.reserved_quantity, 1)
        client.get_refund.side_effect = None
        client.get_refund.return_value = _yk_refund_payload(
            self.payment, refund_id="rf-down", amount="1000.00"
        )
        sync_refund_from_yookassa("rf-down", client=client)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)
        self.assertEqual(self.order.status, Order.STATUS_CANCELLED)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 0)

    def test_local_failure_rolls_back_payment_and_stock(self):
        client = self._refund("rf-boom", "1000.00")
        with patch(
            "apps.orders.services.cancel_order_and_release_stock",
            side_effect=RuntimeError("disk"),
        ):
            with self.assertRaises(RuntimeError):
                sync_refund_from_yookassa("rf-boom", client=client)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_PAID)
        self.assertIsNone(self.payment.refunded_amount)
        self.assertEqual(self.order.status, Order.STATUS_CONFIRMED)
        self.assertEqual(self.stock.reserved_quantity, 1)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(PaymentRefund.objects.count(), 0)
