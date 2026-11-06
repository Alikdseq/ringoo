"""
Регрессия безопасности оплаты и доступа к заказам/платежам.

Все HTTP к Сберу замоканы. Цель: клиент не может подтвердить оплату
подменой полей; чужой заказ/платёж недоступен; callback без банка не ставит paid.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.admin_api.permissions import RINGOO_GROUP_USERS
from apps.orders.models import Order, OrderItem
from apps.orders.serializers import OrderCreateSerializer
from apps.payments.models import Payment
from apps.payments.services import handle_sber_callback, sync_payment_from_bank
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser


def _catalog_order(**kwargs):
    cat = Category.objects.create(title="Cat", slug=f"sec-c-{Category.objects.count()}")
    product = Product.objects.create(
        title="Phone",
        slug=f"sec-p-{Product.objects.count()}",
        price=Decimal("1000.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"sec-s-{Store.objects.count()}", address="a", city="c"
    )
    Stock.objects.create(product=product, store=store, quantity=10, reserved_quantity=0)
    defaults = dict(
        full_name="Иван",
        phone="79001112233",
        email="a@example.com",
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


def _pending_payment(order: Order, *, merchant: str = "secpay1") -> Payment:
    return Payment.objects.create(
        order=order,
        status=Payment.STATUS_PENDING,
        amount=order.total_amount,
        amount_kopecks=100000,
        merchant_order_number=merchant,
        sber_order_id="11111111-1111-1111-1111-111111111111",
        form_url="https://ecomtest.sberbank.ru/pp/x",
        currency="643",
    )


@override_settings(
    SBER_ECOM_ENABLED=True,
    SBER_ECOM_USERNAME="u",
    SBER_ECOM_PASSWORD="p",
    SBER_ECOM_BASE_URL="https://ecomtest.sberbank.ru",
    FRONTEND_URL="https://shop.test",
    SBER_ECOM_CALLBACK_TOKEN="",
)
class PaymentForgerySecurityTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    def test_client_cannot_set_order_paid_via_create_fields(self):
        """Mass-assignment: status/paid в create не принимаются."""
        order, product, store = _catalog_order()
        ser = OrderCreateSerializer(
            data={
                "full_name": "X",
                "phone": "79001112233",
                "delivery_type": Order.DELIVERY_PICKUP,
                "store": str(store.id),
                "payment_type": Order.PAYMENT_ONLINE,
                "items": [{"product_id": str(product.id), "quantity": 1}],
                "total_amount": "1.00",
                "delivery_cost": "999.00",
                "consent_personal_data": True,
                "status": "confirmed",
                "paid": True,
                "is_paid": True,
                "payment_id": "evil",
            }
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.validated_data["delivery_cost"], Decimal("0"))
        self.assertEqual(ser.validated_data["total_amount"], Decimal("1000.00"))
        self.assertNotIn("status", ser.validated_data)
        self.assertNotIn("paid", ser.validated_data)
        self.assertNotIn("is_paid", ser.validated_data)
        # исходный заказ в БД не трогаем этим serializer.validate
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_callback_payload_status_alone_does_not_mark_paid(self):
        """Callback с status=1 без подтверждения банка не ставит paid."""
        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="cbforge")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 0,  # ещё не оплачен
            "actionCode": -100,
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
                "paid": True,
            },
            client=mock_client,
        )
        payment.refresh_from_db()
        self.assertNotEqual(payment.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_missing_bank_amount_does_not_confirm_paid(self):
        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="noamt")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
            # amount отсутствует
        }
        updated = sync_payment_from_bank(payment, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_FAILED)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_foreign_order_number_in_bank_response_rejected(self):
        """Чужой/чужой merchant orderNumber в ответе банка ≠ наш Payment."""
        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="mine-order")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": "someone-elses-payment",
            "currency": "643",
        }
        updated = sync_payment_from_bank(payment, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_FAILED)
        self.assertIn("orderNumber", updated.error_message)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_currency_mismatch_rejected(self):
        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="cur1")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "840",
        }
        updated = sync_payment_from_bank(payment, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_FAILED)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_sber_timeout_does_not_mark_paid(self):
        from integrations.sber.client import SberEcomError

        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="to1")
        mock_client = MagicMock()
        mock_client.get_order_status.side_effect = SberEcomError("timeout")
        with self.assertRaises(Exception):
            sync_payment_from_bank(payment, client=mock_client)
        payment.refresh_from_db()
        self.assertNotEqual(payment.status, Payment.STATUS_PAID)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_sber_http_500_does_not_mark_paid(self):
        from integrations.sber.client import SberEcomError

        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="e500")
        mock_client = MagicMock()
        mock_client.get_order_status.side_effect = SberEcomError(
            "bank 500", error_code="7", payload={"errorCode": "7"}
        )
        with self.assertRaises(Exception):
            sync_payment_from_bank(payment, client=mock_client)
        payment.refresh_from_db()
        self.assertNotEqual(payment.status, Payment.STATUS_PAID)

    def test_unknown_sber_status_does_not_mark_paid(self):
        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="unk")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 99,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        updated = sync_payment_from_bank(payment, client=mock_client)
        self.assertNotEqual(updated.status, Payment.STATUS_PAID)

    def test_repeat_callback_idempotent_no_double_confirm(self):
        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="idemcb")
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
            {"mdOrder": payment.sber_order_id, "operation": "deposited", "status": 1},
            client=mock_client,
        )
        handle_sber_callback(
            {"mdOrder": payment.sber_order_id, "operation": "deposited", "status": 1},
            client=mock_client,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        self.assertEqual(
            Payment.objects.filter(order=order, status=Payment.STATUS_PAID).count(), 1
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)

    def test_second_payment_cannot_become_paid_when_order_already_paid(self):
        order, _, _ = _catalog_order(status=Order.STATUS_CONFIRMED)
        Payment.objects.create(
            order=order,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="already-paid",
            paid_at=timezone.now(),
            currency="643",
        )
        duplicate = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="dup-try",
            sber_order_id="22222222-2222-2222-2222-222222222222",
            form_url="https://ecomtest.sberbank.ru/pp/y",
            currency="643",
        )
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": duplicate.merchant_order_number,
            "currency": "643",
        }
        updated = sync_payment_from_bank(duplicate, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_FAILED)
        self.assertEqual(
            Payment.objects.filter(order=order, status=Payment.STATUS_PAID).count(), 1
        )

    def test_pay_endpoint_ignores_client_amount_and_status(self):
        from apps.orders.guest_access import issue_guest_access_token

        order, _, _ = _catalog_order()
        guest_token = issue_guest_access_token(order)
        mock_client = MagicMock()
        mock_client.register_order.return_value = {
            "orderId": "33333333-3333-3333-3333-333333333333",
            "formUrl": "https://ecomtest.sberbank.ru/pp/pay",
            "raw": {"errorCode": "0"},
        }
        with patch("apps.payments.services.SberEcomClient", return_value=mock_client):
            resp = self.api.post(
                f"/api/v1/orders/{order.id}/pay/",
                {
                    "phone": "79001112233",
                    "order_number": order.order_number,
                    "guest_token": guest_token,
                    "amount": "1.00",
                    "amount_kopecks": 1,
                    "status": "paid",
                    "paid": True,
                    "payment_id": "attacker",
                },
                format="json",
            )
        self.assertEqual(resp.status_code, 200)
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.amount_kopecks, 100000)
        self.assertEqual(payment.status, Payment.STATUS_REGISTERED)
        self.assertEqual(
            mock_client.register_order.call_args.kwargs["amount_kopecks"], 100000
        )

    def test_payment_status_get_does_not_accept_paid_query(self):
        from apps.orders.guest_access import issue_guest_access_token

        order, _, _ = _catalog_order()
        guest_token = issue_guest_access_token(order)
        payment = _pending_payment(order, merchant="qpaid")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 0,
            "actionCode": -100,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        with patch("apps.payments.services.SberEcomClient", return_value=mock_client):
            resp = self.api.get(
                f"/api/v1/orders/{order.id}/payment/",
                {
                    "phone": "79001112233",
                    "order_number": order.order_number,
                    "guest_token": guest_token,
                    "status": "paid",
                    "paid": "true",
                },
            )
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertNotEqual(payment.status, Payment.STATUS_PAID)

    @override_settings(SBER_ECOM_CALLBACK_TOKEN="expected-secret-token")
    def test_callback_rejected_without_token_when_configured(self):
        resp = self.api.post(
            "/api/v1/payments/sber/callback/",
            {"mdOrder": "x", "operation": "deposited", "status": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn("expected-secret-token", str(resp.data))
        self.assertNotIn("token", str(resp.data).lower())

    @override_settings(SBER_ECOM_CALLBACK_TOKEN="expected-secret-token")
    def test_callback_rejected_wrong_token(self):
        resp = self.api.post(
            "/api/v1/payments/sber/callback/?token=wrong-token-value",
            {"mdOrder": "x", "operation": "deposited", "status": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    @override_settings(
        SBER_ECOM_CALLBACK_TOKEN="",
        SBER_ECOM_CALLBACK_TOKEN_REQUIRED=True,
        DEBUG=False,
    )
    def test_callback_rejected_when_token_required_but_unset(self):
        """Staging/prod fail-closed: без секрета в env callback не принимается."""
        resp = self.api.post(
            "/api/v1/payments/sber/callback/",
            {"mdOrder": "x", "operation": "deposited", "status": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    @override_settings(
        SBER_ECOM_CALLBACK_TOKEN="",
        SBER_ECOM_CALLBACK_TOKEN_REQUIRED=False,
        DEBUG=True,
    )
    def test_callback_allowed_without_token_in_dev_mode(self):
        resp = self.api.post(
            "/api/v1/payments/sber/callback/",
            {
                "mdOrder": "00000000-0000-0000-0000-000000000000",
                "operation": "deposited",
                "status": 1,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("ok"))

    @override_settings(SBER_ECOM_CALLBACK_TOKEN="expected-secret-token")
    def test_callback_accepted_with_query_token_still_needs_bank(self):
        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="tokpay")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        with patch("apps.payments.services.SberEcomClient", return_value=mock_client):
            resp = self.api.post(
                "/api/v1/payments/sber/callback/?token=expected-secret-token",
                {
                    "mdOrder": payment.sber_order_id,
                    "operation": "deposited",
                    "status": 1,
                },
                format="json",
            )
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)

    @override_settings(SBER_ECOM_CALLBACK_TOKEN="expected-secret-token")
    def test_callback_accepted_with_header_token(self):
        order, _, _ = _catalog_order()
        payment = _pending_payment(order, merchant="tokhdr")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        with patch("apps.payments.services.SberEcomClient", return_value=mock_client):
            resp = self.api.post(
                "/api/v1/payments/sber/callback/",
                {
                    "mdOrder": payment.sber_order_id,
                    "operation": "deposited",
                    "status": 1,
                },
                format="json",
                HTTP_X_SBER_CALLBACK_TOKEN="expected-secret-token",
            )
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)

    def test_late_payment_on_cancelled_goes_needs_review_not_silent_paid(self):
        order, _, _ = _catalog_order(status=Order.STATUS_CANCELLED)
        payment = _pending_payment(order, merchant="latepay")
        mock_client = MagicMock()
        mock_client.get_order_status.return_value = {
            "errorCode": "0",
            "orderStatus": 2,
            "actionCode": 0,
            "amount": 100000,
            "orderNumber": payment.merchant_order_number,
            "currency": "643",
        }
        with override_settings(LATE_ONLINE_PAYMENT_POLICY="manual"):
            updated = sync_payment_from_bank(payment, client=mock_client)
        self.assertEqual(updated.status, Payment.STATUS_NEEDS_REVIEW)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)


@override_settings(SBER_ECOM_ENABLED=True, FRONTEND_URL="https://shop.test")
class OrderPaymentAccessSecurityTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = CustomUser.objects.create_user(
            phone="79001110001", password="pass12345"
        )
        self.other = CustomUser.objects.create_user(
            phone="79001110002", password="pass12345"
        )

    def test_user_b_cannot_read_user_a_order_detail(self):
        order, _, _ = _catalog_order(user=self.owner, phone=self.owner.phone)
        self.api.force_authenticate(user=self.other)
        resp = self.api.get(f"/api/v1/orders/{order.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_user_b_cannot_pay_user_a_order(self):
        order, _, _ = _catalog_order(user=self.owner, phone=self.owner.phone)
        self.api.force_authenticate(user=self.other)
        resp = self.api.post(f"/api/v1/orders/{order.id}/pay/", {}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Payment.objects.filter(order=order).count(), 0)

    def test_user_b_cannot_cancel_user_a_order(self):
        order, _, _ = _catalog_order(user=self.owner, phone=self.owner.phone)
        self.api.force_authenticate(user=self.other)
        resp = self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json")
        self.assertEqual(resp.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_guest_wrong_phone_cannot_access_payment(self):
        order, _, _ = _catalog_order()
        _pending_payment(order, merchant="guestph")
        resp = self.api.get(
            f"/api/v1/orders/{order.id}/payment/",
            {"phone": "79009999999", "order_number": order.order_number},
        )
        self.assertEqual(resp.status_code, 403)

    def test_guest_phone_alone_cannot_pay(self):
        """SEC-H5: UUID + phone без order_number — отказ."""
        order, _, _ = _catalog_order()
        resp = self.api.post(
            f"/api/v1/orders/{order.id}/pay/",
            {"phone": order.phone},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Payment.objects.filter(order=order).count(), 0)

    def test_guest_phone_and_order_number_without_token_denied(self):
        """SEC-006 final: phone+order_number без guest_token — отказ."""
        order, _, _ = _catalog_order()
        resp = self.api.post(
            f"/api/v1/orders/{order.id}/pay/",
            {"phone": order.phone, "order_number": order.order_number},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_guest_token_passes_access_gate(self):
        """Гость с guest_token проходит access gate (дальше Sber может быть выкл.)."""
        from apps.orders.guest_access import issue_guest_access_token

        order, _, _ = _catalog_order()
        guest_token = issue_guest_access_token(order)
        resp = self.api.post(
            f"/api/v1/orders/{order.id}/pay/",
            {
                "phone": order.phone,
                "order_number": order.order_number,
                "guest_token": guest_token,
            },
            format="json",
        )
        # 403 = access denied; любой другой код = gate пройден (Sber off → 4xx/502)
        self.assertNotEqual(resp.status_code, 403)

    def test_guest_cannot_access_order_by_uuid_alone(self):
        order, _, _ = _catalog_order()
        resp = self.api.get(f"/api/v1/orders/{order.id}/")
        self.assertIn(resp.status_code, (401, 403))

    def test_anon_cannot_use_guessable_order_number_without_phone(self):
        order, _, _ = _catalog_order()
        resp = self.api.get(
            "/api/v1/orders/track/",
            {"order_number": order.order_number},
        )
        self.assertEqual(resp.status_code, 400)


class StaffEscalationSecurityTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        Group.objects.get_or_create(name=RINGOO_GROUP_USERS)
        self.staff = CustomUser.objects.create_user(
            phone="79002000001", password="pass12345", is_staff=True
        )
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_USERS))
        self.victim = CustomUser.objects.create_user(
            phone="79002000002", password="pass12345", is_staff=False
        )
        self.super = CustomUser.objects.create_superuser(
            phone="79002000003", password="pass12345"
        )

    def test_non_superuser_staff_cannot_grant_is_staff(self):
        self.api.force_authenticate(user=self.staff)
        resp = self.api.patch(
            f"/api/v1/admin/users/{self.victim.id}/patch/",
            {"is_staff": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.victim.refresh_from_db()
        self.assertFalse(self.victim.is_staff)

    def test_superuser_can_grant_is_staff(self):
        self.super.groups.add(Group.objects.get(name=RINGOO_GROUP_USERS))
        self.api.force_authenticate(user=self.super)
        resp = self.api.patch(
            f"/api/v1/admin/users/{self.victim.id}/patch/",
            {"is_staff": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.victim.refresh_from_db()
        self.assertTrue(self.victim.is_staff)
