"""
R38: инициация денежных возвратов заблокирована по умолчанию и в production.

Входящий refund.succeeded (GET /refunds/{id}) не вызывает create_refund.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.payments.models import Payment
from apps.payments.refund_policy import (
    RefundInitiationDisabled,
    assert_refund_initiation_allowed,
    refund_initiation_allowed,
)
from apps.payments.yookassa_service import handle_yookassa_webhook
from apps.returns.models import ReturnRequest
from apps.returns.services import initiate_money_refund
from integrations.sber.client import SberEcomClient
from integrations.yookassa.client import YooKassaClient
from tests.test_int004_int005_yookassa_refund_metadata import (
    _order,
    _payment,
    _yk_refund_payload,
)


class RefundPolicyFlagTests(TestCase):
    def test_default_disallows_initiation(self):
        self.assertFalse(refund_initiation_allowed())
        with self.assertRaises(RefundInitiationDisabled):
            assert_refund_initiation_allowed()

    @override_settings(PAYMENTS_REFUND_INITIATION_ENABLED=True)
    def test_explicit_enable_allows(self):
        self.assertTrue(refund_initiation_allowed())
        assert_refund_initiation_allowed()


@override_settings(PAYMENTS_REFUND_INITIATION_ENABLED=False)
class YooKassaCreateRefundBlockedTests(TestCase):
    def test_create_refund_raises_without_http(self):
        client = YooKassaClient.__new__(YooKassaClient)
        with patch.object(YooKassaClient, "_request") as req:
            with self.assertRaises(RefundInitiationDisabled):
                client.create_refund(
                    payment_id="yk-1",
                    amount=Decimal("10.00"),
                    idempotence_key="r38-block",
                )
            req.assert_not_called()

    def test_get_refund_still_allowed(self):
        client = YooKassaClient.__new__(YooKassaClient)
        with patch.object(YooKassaClient, "_request", return_value={"id": "rf-1", "status": "succeeded"}) as req:
            data = client.get_refund("rf-1")
        self.assertEqual(data["id"], "rf-1")
        req.assert_called_once()


@override_settings(PAYMENTS_REFUND_INITIATION_ENABLED=False)
class SberRefundApisBlockedTests(TestCase):
    def test_reverse_and_refund_blocked(self):
        client = SberEcomClient.__new__(SberEcomClient)
        with patch.object(SberEcomClient, "_post") as post:
            with self.assertRaises(RefundInitiationDisabled):
                client.reverse_order(order_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            with self.assertRaises(RefundInitiationDisabled):
                client.refund_order(order_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", amount_kopecks=100)
            post.assert_not_called()


@override_settings(
    RETURNS_ENABLED=True,
    PAYMENTS_REFUND_INITIATION_ENABLED=False,
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
)
class InitiateMoneyRefundBlockedTests(TestCase):
    def setUp(self):
        self.order = _order()
        self.order.payment_status = self.order.PAYMENT_STATUS_PAID
        self.order.save(update_fields=["payment_status"])
        self.payment = _payment(self.order)
        self.rr = ReturnRequest.objects.create(
            number="RET-R38-1",
            order=self.order,
            ground=ReturnRequest.GROUND_QUALITY_OK,
            demand=ReturnRequest.DEMAND_REFUND,
            description="r38",
            requested_refund_amount=Decimal("1000.00"),
            approved_refund_amount=Decimal("1000.00"),
            status=ReturnRequest.STATUS_APPROVED,
        )

    def test_dry_run_does_not_call_provider(self):
        with patch("integrations.yookassa.client.YooKassaClient.create_refund") as cr:
            mr = initiate_money_refund(self.rr, dry_run=True)
        self.assertEqual(mr.status, mr.STATUS_NEEDS_REVIEW)
        cr.assert_not_called()

    def test_live_initiation_blocked(self):
        with patch("integrations.yookassa.client.YooKassaClient.create_refund") as cr:
            with self.assertRaises(RefundInitiationDisabled):
                initiate_money_refund(self.rr, dry_run=False)
            cr.assert_not_called()


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    PAYMENTS_REFUND_INITIATION_ENABLED=False,
    SBER_ECOM_ENABLED=False,
    RETURNS_ENABLED=False,
)
class InboundRefundWebhookDoesNotInitiateTests(TestCase):
    def test_webhook_records_without_create_refund(self):
        order = _order()
        order.payment_status = order.PAYMENT_STATUS_PAID
        order.save(update_fields=["payment_status"])
        payment = _payment(order)
        client = MagicMock()
        client.get_refund.return_value = _yk_refund_payload(payment, refund_id="rf-inbound")
        client.create_refund.side_effect = AssertionError("must not initiate")
        with patch("apps.payments.yookassa_service.YooKassaClient", return_value=client):
            result = handle_yookassa_webhook(
                {"event": "refund.succeeded", "object": {"id": "rf-inbound"}},
                client=client,
            )
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertIsNotNone(result)
        self.assertEqual(payment.status, Payment.STATUS_NEEDS_REVIEW)
        order.refresh_from_db()
        self.assertNotEqual(order.status, "closed")
        client.create_refund.assert_not_called()
        client.get_refund.assert_called()
