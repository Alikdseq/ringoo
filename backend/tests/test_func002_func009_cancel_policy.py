"""FUNC-002 единый cancel + FUNC-009 запрет отмены оплаченного."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.admin_api.permissions import RINGOO_GROUP_ORDERS
from apps.orders.guest_access import issue_guest_access_token
from apps.orders.models import Order, OrderItem
from apps.orders.services import (
    OrderCancelError,
    cancel_order_and_release_stock,
    customer_may_cancel_order,
)
from apps.payments.models import Payment
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.admin_mfa import ADMIN_MFA_CLAIM
from apps.users.models import CustomUser


def _catalog():
    cat = Category.objects.create(title="C", slug=f"fc-{Category.objects.count()}")
    product = Product.objects.create(
        title="P",
        slug=f"fcp-{Product.objects.count()}",
        price=Decimal("500.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"fcs-{Store.objects.count()}", address="a", city="c"
    )
    Stock.objects.create(product=product, store=store, quantity=10, reserved_quantity=1)
    return product, store


def _order(*, user=None, status=Order.STATUS_NEW, payment_type=Order.PAYMENT_CASH):
    product, store = _catalog()
    order = Order.objects.create(
        user=user,
        full_name="Buyer",
        phone=user.phone if user else "79002220001",
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=payment_type,
        status=status,
        total_amount=Decimal("500.00"),
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=1,
        price=Decimal("500.00"),
        item_total=Decimal("500.00"),
    )
    return order, product, store


@override_settings(
    ADMIN_OTP_ENABLED=True,
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class Func002Func009CancelTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
        self.user = CustomUser.objects.create_user(
            phone="79002221111", password="pass12345"
        )
        self.staff = CustomUser.objects.create_user(
            phone="79002222222", password="pass12345", is_staff=True
        )
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))

    def _mfa_auth(self, user):
        token = AccessToken.for_user(user)
        token[ADMIN_MFA_CLAIM] = True
        self.api.force_authenticate(user=user, token=token)

    def test_customer_can_cancel_unpaid(self):
        order, product, store = _order(user=self.user, status=Order.STATUS_NEW)
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 0)

    def test_customer_cannot_cancel_paid_online(self):
        order, product, store = _order(
            user=self.user,
            status=Order.STATUS_CONFIRMED,
            payment_type=Order.PAYMENT_ONLINE,
        )
        Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=50000,
            merchant_order_number="p" * 32,
            paid_at=timezone.now(),
        )
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "paid_order_cancel_forbidden")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 1)

    def test_guest_cannot_cancel_paid(self):
        order, _, _ = _order(
            user=None,
            status=Order.STATUS_CONFIRMED,
            payment_type=Order.PAYMENT_ONLINE,
        )
        token = issue_guest_access_token(order)
        Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=50000,
            merchant_order_number="g" * 32,
            paid_at=timezone.now(),
        )
        resp = self.api.post(
            f"/api/v1/orders/{order.id}/cancel/",
            {
                "order_number": order.order_number,
                "phone": order.phone,
                "guest_token": token,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)

    def test_admin_api_cannot_patch_paid_to_cancelled(self):
        order, product, store = _order(
            user=self.user,
            status=Order.STATUS_CONFIRMED,
            payment_type=Order.PAYMENT_ONLINE,
        )
        Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=50000,
            merchant_order_number="a" * 32,
            paid_at=timezone.now(),
        )
        self._mfa_auth(self.staff)
        resp = self.api.patch(
            f"/api/v1/admin/orders/{order.id}/",
            {"status": Order.STATUS_CANCELLED},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 1)

    def test_admin_api_cancel_unpaid_releases_stock_once(self):
        order, product, store = _order(user=self.user, status=Order.STATUS_NEW)
        self._mfa_auth(self.staff)
        with patch("apps.orders.tasks.enqueue_order_cancel") as enq:
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.api.patch(
                    f"/api/v1/admin/orders/{order.id}/",
                    {"status": Order.STATUS_CANCELLED},
                    format="json",
                )
                self.assertEqual(resp.status_code, 200, resp.content)
                cancel_order_and_release_stock(order, reason="repeat")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        stock = Stock.objects.get(product=product, store=store)
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(enq.call_count, 1)

    def test_service_idempotent_and_can_cancel_flag(self):
        order, _, _ = _order(user=self.user, status=Order.STATUS_NEW)
        self.assertTrue(customer_may_cancel_order(order))
        cancel_order_and_release_stock(order, reason="first")
        cancel_order_and_release_stock(order, reason="second")
        order.refresh_from_db()
        self.assertFalse(customer_may_cancel_order(order))

    def test_paid_service_raises(self):
        order, _, _ = _order(
            user=self.user,
            status=Order.STATUS_CONFIRMED,
            payment_type=Order.PAYMENT_ONLINE,
        )
        Payment.objects.create(
            order=order,
            status=Payment.STATUS_PAID,
            amount=order.total_amount,
            amount_kopecks=50000,
            merchant_order_number="x" * 32,
            paid_at=timezone.now(),
        )
        with self.assertRaises(OrderCancelError):
            cancel_order_and_release_stock(order, reason="bad")
