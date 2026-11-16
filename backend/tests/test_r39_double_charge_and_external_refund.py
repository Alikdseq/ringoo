"""
R39: защита от второй confirmation URL + политика внешнего refund webhook.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentRefund
from apps.payments.services import PaymentError, initiate_online_payment
from apps.payments.yookassa_service import (
    handle_yookassa_webhook,
    initiate_yookassa_payment,
    sync_refund_from_yookassa,
)
from apps.stores.models import Stock
from integrations.yookassa.client import YooKassaError
from tests.test_int004_int005_yookassa_refund_metadata import (
    _order,
    _payment,
    _yk_refund_payload,
)
from tests.test_order_repay import _make_order


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    SBER_ECOM_ENABLED=False,
)
class DoubleChargePreventionTests(TestCase):
    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_expired_still_pending_at_provider_reuses_session(self, MockClient):
        order, _, _ = _make_order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_EXPIRED,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="e" * 32,
            yookassa_payment_id="yk-still-open",
            form_url="",
            last_status_response={
                "confirmation": {"confirmation_url": "https://yoomoney.ru/checkout/payments/v2/contract?orderId=old"}
            },
        )
        api = MockClient.return_value
        api.get_payment.return_value = {
            "id": "yk-still-open",
            "status": "pending",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "confirmation_url": "https://yoomoney.ru/checkout/payments/v2/contract?orderId=old",
            },
            "metadata": {"order_id": str(order.id), "payment_id": str(payment.id)},
            "test": True,
        }
        result = initiate_yookassa_payment(order, client=api)
        self.assertTrue(result.reused)
        self.assertEqual(result.payment.pk, payment.pk)
        self.assertIn("orderId=old", result.form_url)
        api.create_payment.assert_not_called()
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_local_failed_while_provider_pending_blocks_new_session(self, MockClient):
        order, _, _ = _make_order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_FAILED,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="g" * 32,
            yookassa_payment_id="yk-alive",
            form_url="",
            last_status_response={
                "confirmation": {"confirmation_url": "https://pay.example/alive"},
            },
        )
        api = MockClient.return_value
        api.get_payment.return_value = {
            "id": "yk-alive",
            "status": "pending",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "confirmation": {"confirmation_url": "https://pay.example/alive"},
            "metadata": {"order_id": str(order.id), "payment_id": str(payment.id)},
            "test": True,
        }
        result = initiate_online_payment(order)
        self.assertTrue(result.reused)
        api.create_payment.assert_not_called()
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_provider_unreachable_does_not_create_new_session(self, MockClient):
        order, _, _ = _make_order()
        Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_EXPIRED,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="h" * 32,
            yookassa_payment_id="yk-unk",
            form_url="https://pay.example/x",
        )
        MockClient.return_value.get_payment.side_effect = YooKassaError("down", code="yookassa_unreachable")
        with self.assertRaises(PaymentError) as ctx:
            initiate_yookassa_payment(order, client=MockClient.return_value)
        self.assertEqual(ctx.exception.code, "payment_status_unknown")
        MockClient.return_value.create_payment.assert_not_called()
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_confirmed_canceled_allows_new_session(self, MockClient):
        order, _, _ = _make_order()
        old = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_EXPIRED,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="i" * 32,
            yookassa_payment_id="yk-closed",
            form_url="https://pay.example/old",
        )
        api = MockClient.return_value
        api.get_payment.return_value = {
            "id": "yk-closed",
            "status": "canceled",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "cancellation_details": {"reason": "expired_on_timeout"},
            "metadata": {"order_id": str(order.id), "payment_id": str(old.id)},
            "test": True,
        }

        def create_payment(**kwargs):
            p = Payment.objects.filter(order=order).latest("created_at")
            return {
                "id": "yk-new",
                "status": "pending",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "confirmation": {"confirmation_url": "https://pay.example/new"},
                "metadata": {"order_id": str(order.id), "payment_id": str(p.id)},
                "test": True,
            }

        api.create_payment.side_effect = create_payment
        result = initiate_yookassa_payment(order, client=api)
        self.assertFalse(result.reused)
        self.assertEqual(result.form_url, "https://pay.example/new")
        self.assertEqual(Payment.objects.filter(order=order).count(), 2)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_failed_without_yk_id_retries_same_payment_row(self, MockClient):
        order, _, _ = _make_order()
        failed = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_FAILED,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="j" * 32,
            yookassa_payment_id=None,
            form_url="",
            error_message="timeout",
        )
        api = MockClient.return_value

        def create_payment(**kwargs):
            self.assertEqual(str(kwargs["idempotence_key"]), str(failed.id))
            return {
                "id": "yk-retried",
                "status": "pending",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "confirmation": {"confirmation_url": "https://pay.example/retry"},
                "metadata": {"order_id": str(order.id), "payment_id": str(failed.id)},
                "test": True,
            }

        api.create_payment.side_effect = create_payment
        result = initiate_yookassa_payment(order, client=api)
        self.assertFalse(result.reused)
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)
        failed.refresh_from_db()
        self.assertEqual(failed.yookassa_payment_id, "yk-retried")
        self.assertEqual(failed.status, Payment.STATUS_REGISTERED)


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    SBER_ECOM_ENABLED=False,
    RETURNS_ENABLED=False,
    PAYMENTS_REFUND_INITIATION_ENABLED=False,
)
class ExternalRefundPolicyTests(TestCase):
    def setUp(self):
        self.order = _order()
        self.order.payment_status = Order.PAYMENT_STATUS_PAID
        self.order.save(update_fields=["payment_status"])
        self.payment = _payment(self.order)
        self.stock = Stock.objects.get(store=self.order.store)
        self.stock.quantity = 5
        self.stock.reserved_quantity = 1
        self.stock.save(update_fields=["quantity", "reserved_quantity"])

    def test_external_full_refund_no_side_effects(self):
        before_status = self.order.status
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(self.payment, refund_id="rf-r39")
        result = handle_yookassa_webhook(
            {"event": "refund.succeeded", "object": {"id": "rf-r39"}},
            client=client,
        )
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertEqual(self.payment.refunded_amount, Decimal("1000.00"))
        self.assertEqual(self.order.status, before_status)
        self.assertEqual(self.order.payment_status, Order.PAYMENT_STATUS_PAID)
        self.assertEqual(self.stock.reserved_quantity, 1)
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(PaymentRefund.objects.count(), 1)
        client.create_refund.assert_not_called()

    def test_external_refund_idempotent(self):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(self.payment, refund_id="rf-once")
        handle_yookassa_webhook({"event": "refund.succeeded", "object": {"id": "rf-once"}}, client=client)
        handle_yookassa_webhook({"event": "refund.succeeded", "object": {"id": "rf-once"}}, client=client)
        self.assertEqual(PaymentRefund.objects.count(), 1)
        self.assertEqual(client.get_refund.call_count, 1)

    def test_amount_mismatch_not_accepted(self):
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(self.payment, refund_id="rf-bad", amount="1000.01")
        sync_refund_from_yookassa("rf-bad", client=client)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_NEEDS_REVIEW)
        self.assertIsNone(self.payment.refunded_amount)
        self.assertEqual(PaymentRefund.objects.count(), 0)

    def test_get_error_does_not_accept_unconfirmed(self):
        client = MagicMock()
        client.get_refund.side_effect = YooKassaError("down", code="yookassa_unreachable")
        with self.assertRaises(PaymentError):
            sync_refund_from_yookassa("rf-down", client=client)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_PAID)
        self.assertEqual(PaymentRefund.objects.count(), 0)
