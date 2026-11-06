"""Повторная оплата из карточки заказа: eligibility + POST /pay/."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.payments.eligibility import evaluate_order_payment_eligibility
from apps.payments.models import Payment
from apps.payments.services import PaymentError, initiate_online_payment
from apps.payments.yookassa_service import initiate_yookassa_payment
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser
from integrations.yookassa.client import YooKassaError


def _catalog():
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
    Stock.objects.create(product=product, store=store, quantity=20, reserved_quantity=0)
    return product, store


def _make_order(**kwargs):
    product, store = _catalog()
    user = kwargs.pop("user", None)
    defaults = dict(
        user=user,
        full_name="Иван",
        phone="79001112233",
        email="t@example.com",
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
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    YOOKASSA_API_URL="https://api.yookassa.ru/v3",
    SBER_ECOM_ENABLED=False,
)
class OrderRepayEligibilityTests(TestCase):
    def test_new_online_can_pay(self):
        order, _, _ = _make_order(status=Order.STATUS_NEW)
        elig = evaluate_order_payment_eligibility(order)
        self.assertTrue(elig.can_pay)
        self.assertEqual(elig.code, "ok")

    def test_confirmed_online_can_pay(self):
        order, _, _ = _make_order(status=Order.STATUS_CONFIRMED)
        self.assertTrue(evaluate_order_payment_eligibility(order).can_pay)

    def test_cancelled_cannot_pay(self):
        order, _, _ = _make_order(status=Order.STATUS_CANCELLED)
        elig = evaluate_order_payment_eligibility(order)
        self.assertFalse(elig.can_pay)
        self.assertEqual(elig.code, "order_cancelled")

    def test_completed_cannot_pay(self):
        order, _, _ = _make_order(status=Order.STATUS_COMPLETED)
        elig = evaluate_order_payment_eligibility(order)
        self.assertFalse(elig.can_pay)
        self.assertEqual(elig.code, "order_completed")

    def test_cash_cannot_pay(self):
        order, _, _ = _make_order(payment_type=Order.PAYMENT_CASH)
        elig = evaluate_order_payment_eligibility(order)
        self.assertFalse(elig.can_pay)
        self.assertEqual(elig.code, "not_online")

    def test_paid_payment_blocks(self):
        order, _, _ = _make_order()
        Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="p" * 32,
        )
        elig = evaluate_order_payment_eligibility(order)
        self.assertFalse(elig.can_pay)
        self.assertEqual(elig.code, "already_paid")


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    YOOKASSA_API_URL="https://api.yookassa.ru/v3",
    SBER_ECOM_ENABLED=False,
)
class OrderRepayApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = CustomUser.objects.create_user(phone="79005551122", password="pass12345")
        self.other = CustomUser.objects.create_user(phone="79005553344", password="pass12345")

    def test_serializer_can_pay_on_detail(self):
        order, _, _ = _make_order(user=self.user, status=Order.STATUS_NEW)
        self.api.force_authenticate(user=self.user)
        r = self.api.get(f"/api/v1/orders/{order.id}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data.get("can_pay"))
        self.assertIn("payment_status", r.data)

    def test_pay_forbidden_for_other_user(self):
        order, _, _ = _make_order(user=self.user)
        self.api.force_authenticate(user=self.other)
        r = self.api.post(f"/api/v1/orders/{order.id}/pay/", {}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_pay_rejected_for_cancelled(self):
        order, _, _ = _make_order(user=self.user, status=Order.STATUS_CANCELLED)
        self.api.force_authenticate(user=self.user)
        r = self.api.post(f"/api/v1/orders/{order.id}/pay/", {}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data.get("code"), "order_cancelled")

    def test_pay_rejected_for_paid(self):
        order, _, _ = _make_order(user=self.user)
        Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="q" * 32,
        )
        self.api.force_authenticate(user=self.user)
        r = self.api.post(f"/api/v1/orders/{order.id}/pay/", {}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data.get("code"), "already_paid")

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_pay_new_order_returns_confirmation_url(self, MockClient):
        order, _, _ = _make_order(user=self.user, status=Order.STATUS_NEW)
        api = MockClient.return_value

        def create_payment(**kwargs):
            p = Payment.objects.filter(order=order).latest("created_at")
            return {
                "id": "yk-repay-1",
                "status": "pending",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "confirmation_url": "https://yoomoney.ru/checkout/payments/v2/contract?orderId=1",
                },
                "paid": False,
                "test": True,
                "metadata": {"order_id": str(order.id), "payment_id": str(p.id)},
            }

        api.create_payment.side_effect = create_payment
        self.api.force_authenticate(user=self.user)
        r = self.api.post(f"/api/v1/orders/{order.id}/pay/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data.get("confirmation_url") or r.data.get("form_url"))
        self.assertFalse(r.data.get("reused"))

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_unknown_status_does_not_create_second_payment(self, MockClient):
        order, _, _ = _make_order(user=self.user)
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="u" * 32,
            yookassa_payment_id="yk-unknown",
            form_url="https://pay.example/x",
        )
        MockClient.return_value.get_payment.side_effect = YooKassaError(
            "down", code="yookassa_http_error"
        )
        with self.assertRaises(PaymentError) as ctx:
            initiate_yookassa_payment(order, client=MockClient.return_value)
        self.assertEqual(ctx.exception.code, "payment_status_unknown")
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PENDING)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_failed_payment_allows_new_payment(self, MockClient):
        order, _, _ = _make_order(user=self.user)
        Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_FAILED,
            amount=order.total_amount,
            amount_kopecks=100000,
            currency="RUB",
            merchant_order_number="f" * 32,
            yookassa_payment_id="yk-old-fail",
            form_url="https://pay.example/old",
        )
        api = MockClient.return_value

        def create_payment(**kwargs):
            p = Payment.objects.filter(order=order).latest("created_at")
            return {
                "id": "yk-new-ok",
                "status": "pending",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "confirmation_url": "https://yoomoney.ru/checkout/payments/v2/contract?orderId=2",
                },
                "paid": False,
                "test": True,
                "metadata": {"order_id": str(order.id), "payment_id": str(p.id)},
            }

        api.create_payment.side_effect = create_payment
        result = initiate_online_payment(order)
        self.assertFalse(result.reused)
        self.assertEqual(Payment.objects.filter(order=order).count(), 2)
