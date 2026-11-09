"""Входящие события 1С: статус заказа и оплата в магазине."""

from __future__ import annotations

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import OneCInboundEvent, Order
from apps.payments.models import Payment
from apps.products.models import Category, Product
from apps.stores.models import Store

User = get_user_model()

URL = "/api/v1/integrations/1c/orders/status/"
TOKEN = "test-onec-inbound-token-32chars-xx"


def _auth():
    return {"HTTP_X_ONEC_TOKEN": TOKEN}


@override_settings(ONE_C_INCOMING_TOKEN=TOKEN)
class OneCInboundOrderStatusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store = Store.objects.create(
            name="Test Store",
            slug="test-store",
            address="Addr",
            city="City",
            is_active=True,
        )
        cat = Category.objects.create(title="Phones", slug="phones")
        self.product = Product.objects.create(
            title="Phone",
            slug="phone",
            category=cat,
            price=Decimal("25990.00"),
            is_active=True,
        )
        self.order = Order.objects.create(
            order_number="ORD-20261109-aaaa01",
            full_name="Test User",
            phone="+79001234567",
            delivery_type=Order.DELIVERY_PICKUP,
            store=self.store,
            payment_type=Order.PAYMENT_CASH,
            status=Order.STATUS_NEW,
            payment_status=Order.PAYMENT_STATUS_UNPAID,
            total_amount=Decimal("25990.00"),
            consent_personal_data=True,
        )

    def test_unauthorized_without_token(self):
        r = self.client.post(URL, {"event_id": "e1", "order_number": self.order.order_number}, format="json")
        self.assertEqual(r.status_code, 401)

    @override_settings(ONE_C_INCOMING_TOKEN="")
    def test_disabled_without_env_token(self):
        r = self.client.post(
            URL,
            {
                "event_id": "e-disabled",
                "order_number": self.order.order_number,
                "status": "processing",
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 503)

    def test_invalid_json_object(self):
        r = self.client.post(URL, ["not", "object"], format="json", **_auth())
        self.assertEqual(r.status_code, 400)

    def test_order_not_found(self):
        r = self.client.post(
            URL,
            {
                "event_id": "e-404",
                "order_number": "ORD-MISSING",
                "status": "processing",
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.data["error"], "order_not_found")

    def test_new_to_processing(self):
        r = self.client.post(
            URL,
            {
                "event_id": "e-proc",
                "order_number": self.order.order_number,
                "status": "processing",
                "source": "1c",
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PROCESSING)

    def test_processing_to_ready(self):
        self.order.status = Order.STATUS_PROCESSING
        self.order.save(update_fields=["status"])
        r = self.client.post(
            URL,
            {
                "event_id": "e-ready",
                "order_number": self.order.order_number,
                "status": "ready",
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_READY)

    def test_close_completed(self):
        self.order.status = Order.STATUS_READY
        self.order.save(update_fields=["status"])
        r = self.client.post(
            URL,
            {
                "event_id": "e-done",
                "order_number": self.order.order_number,
                "status": "closed",
                "result": "completed",
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_CLOSED)
        self.assertEqual(self.order.closure_result, Order.CLOSURE_COMPLETED)

    @mock.patch("apps.orders.tasks.enqueue_order_cancel")
    def test_cancel_skips_outbound_onec(self, enqueue_cancel):
        self.order.status = Order.STATUS_PROCESSING
        self.order.save(update_fields=["status"])
        r = self.client.post(
            URL,
            {
                "event_id": "e-cancel",
                "order_number": self.order.order_number,
                "status": "closed",
                "result": "cancelled",
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_cancelled())
        enqueue_cancel.assert_not_called()

    def test_cash_payment(self):
        r = self.client.post(
            URL,
            {
                "event_id": "e-pay-cash",
                "order_number": self.order.order_number,
                "payment": {
                    "status": "paid",
                    "method": "cash",
                    "amount": "25990.00",
                    "currency": "RUB",
                    "payment_reference": "PAY-1",
                },
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PAYMENT_STATUS_PAID)

    def test_card_on_pickup_payment(self):
        self.order.payment_type = Order.PAYMENT_CARD_ON_DELIVERY
        self.order.save(update_fields=["payment_type"])
        r = self.client.post(
            URL,
            {
                "event_id": "e-pay-card",
                "order_number": self.order.order_number,
                "payment": {
                    "status": "paid",
                    "method": "card_on_pickup",
                    "amount": "25990.00",
                    "currency": "RUB",
                },
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PAYMENT_STATUS_PAID)

    def test_online_paid_not_reset_by_onec(self):
        self.order.payment_type = Order.PAYMENT_ONLINE
        self.order.payment_status = Order.PAYMENT_STATUS_PAID
        self.order.save(update_fields=["payment_type", "payment_status"])
        Payment.objects.create(
            order=self.order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PAID,
            amount=Decimal("25990.00"),
            amount_kopecks=2599000,
            merchant_order_number="m-1",
            yookassa_payment_id="yk-1",
        )
        r = self.client.post(
            URL,
            {
                "event_id": "e-online-ok",
                "order_number": self.order.order_number,
                "payment": {
                    "status": "paid",
                    "method": "online",
                    "amount": "25990.00",
                    "currency": "RUB",
                },
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PAYMENT_STATUS_PAID)
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)

    def test_duplicate_event_id(self):
        body = {
            "event_id": "e-dup",
            "order_number": self.order.order_number,
            "status": "processing",
        }
        r1 = self.client.post(URL, body, format="json", **_auth())
        r2 = self.client.post(URL, body, format="json", **_auth())
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.data["duplicate"])
        self.assertEqual(OneCInboundEvent.objects.filter(event_id="e-dup").count(), 1)

    def test_invalid_transition(self):
        r = self.client.post(
            URL,
            {
                "event_id": "e-bad",
                "order_number": self.order.order_number,
                "status": "ready",
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 409)

    def test_amount_mismatch(self):
        r = self.client.post(
            URL,
            {
                "event_id": "e-amt",
                "order_number": self.order.order_number,
                "payment": {
                    "status": "paid",
                    "method": "cash",
                    "amount": "1.00",
                    "currency": "RUB",
                },
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["error"], "amount_mismatch")

    def test_repeat_payment_idempotent(self):
        body = {
            "event_id": "e-pay-once",
            "order_number": self.order.order_number,
            "payment": {
                "status": "paid",
                "method": "cash",
                "amount": "25990.00",
                "currency": "RUB",
            },
        }
        self.assertEqual(self.client.post(URL, body, format="json", **_auth()).status_code, 200)
        body2 = {**body, "event_id": "e-pay-twice"}
        r = self.client.post(URL, body2, format="json", **_auth())
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PAYMENT_STATUS_PAID)

    def test_cannot_change_closed_order(self):
        self.order.status = Order.STATUS_CLOSED
        self.order.closure_result = Order.CLOSURE_COMPLETED
        self.order.save(update_fields=["status", "closure_result"])
        r = self.client.post(
            URL,
            {
                "event_id": "e-reopen",
                "order_number": self.order.order_number,
                "status": "processing",
            },
            format="json",
            **_auth(),
        )
        self.assertEqual(r.status_code, 409)
