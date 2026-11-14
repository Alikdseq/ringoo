"""
Fix-pack B (B8-010): контракт отмены FSM v2 + резервы + SEC-006.

Правильный исход отмены: status=closed, closure_result=cancelled.
Физический Stock.quantity не меняется; reserved снимается идемпотентно.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.admin_api.permissions import RINGOO_GROUP_ORDERS
from apps.orders.guest_access import issue_guest_access_token
from apps.orders.models import Order, OrderItem
from apps.orders.services import cancel_order_and_release_stock, customer_may_cancel_order
from apps.orders.services.transitions import (
    OrderTransitionError,
    transition_order_status,
)
from apps.payments.models import Payment
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser
from tests.order_fsm_assertions import assert_order_cancelled, assert_order_not_cancelled


def _stocked(*, qty=10, reserved=0, series=""):
    cat = Category.objects.create(
        title="FPB", slug=f"fpb-c-{Category.objects.count()}"
    )
    product = Product.objects.create(
        title="FPB P",
        slug=f"fpb-p-{Product.objects.count()}",
        price=Decimal("100.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="FPB Store",
        slug=f"fpb-s-{Store.objects.count()}",
        address="a",
        city="Москва",
        is_active=True,
    )
    stock = Stock.objects.create(
        product=product,
        store=store,
        quantity=qty,
        reserved_quantity=reserved,
        onec_series_id=series or "",
    )
    return product, store, stock


def _order(
    *,
    user=None,
    product=None,
    store=None,
    qty=1,
    reserved=1,
    status=Order.STATUS_NEW,
    payment_type=Order.PAYMENT_CASH,
    payment_status=Order.PAYMENT_STATUS_UNPAID,
    series="",
):
    if product is None or store is None:
        product, store, stock = _stocked(reserved=reserved, series=series)
    else:
        stock = Stock.objects.get(product=product, store=store, onec_series_id=series or "")
        stock.reserved_quantity = reserved
        stock.save(update_fields=["reserved_quantity"])
    order = Order.objects.create(
        user=user,
        full_name="Buyer",
        phone=user.phone if user else "79007770001",
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=payment_type,
        payment_status=payment_status,
        total_amount=product.price * qty,
        status=status,
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=qty,
        price=product.price,
        item_total=product.price * qty,
        onec_series_id=series or "",
    )
    return order, product, store, stock


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
    ADMIN_OTP_ENABLED=False,
    ONE_C_API_ENABLED=False,
    ONE_C_ORDER_SYNC_ENABLED=False,
)
class FixPackBCancelContractTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
        self.api = APIClient()
        self.user = CustomUser.objects.create_user(
            phone="79007771111", password="pass12345"
        )
        self.other = CustomUser.objects.create_user(
            phone="79007772222", password="pass12345"
        )

    def test_fsm_cancel_alias_becomes_closed_cancelled(self):
        order, product, store, stock = _order(user=self.user, reserved=1)
        qty_before = stock.quantity
        with patch("apps.orders.tasks.enqueue_order_cancel"):
            locked = transition_order_status(
                order, "cancelled", reason="fpb_alias"
            )
        assert_order_cancelled(self, locked)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, qty_before)
        self.assertEqual(stock.reserved_quantity, 0)

    def test_fsm_completed_releases_reserve_without_qty_change(self):
        order, _, _, stock = _order(user=self.user, reserved=1)
        qty_before = stock.quantity
        locked = transition_order_status(
            order,
            Order.STATUS_CLOSED,
            closure_result=Order.CLOSURE_COMPLETED,
            reason="fpb_complete",
        )
        self.assertTrue(locked.is_fulfilled())
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, qty_before)
        self.assertEqual(stock.reserved_quantity, 0)
        # повторное completed — без повторного снятия
        stock.reserved_quantity = 3
        stock.save(update_fields=["reserved_quantity"])
        transition_order_status(
            locked,
            Order.STATUS_CLOSED,
            closure_result=Order.CLOSURE_COMPLETED,
            reason="fpb_complete_again",
        )
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 3)

    def test_forbidden_cancel_after_completed(self):
        order, _, _, stock = _order(user=self.user, reserved=0)
        transition_order_status(
            order,
            Order.STATUS_CLOSED,
            closure_result=Order.CLOSURE_COMPLETED,
        )
        with self.assertRaises(OrderTransitionError):
            transition_order_status(order, "cancelled", reason="fpb_bad")
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 0)

    def test_owner_cancel_ok_other_forbidden_anon_forbidden(self):
        order, _, _, stock = _order(user=self.user, reserved=1)
        qty_before = stock.quantity

        self.api.force_authenticate(user=self.other)
        self.assertEqual(
            self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json").status_code,
            403,
        )
        assert_order_not_cancelled(self, order)

        self.api.force_authenticate(user=None)
        self.assertEqual(
            self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json").status_code,
            403,
        )

        self.api.force_authenticate(user=self.user)
        with patch("apps.orders.tasks.enqueue_order_cancel"):
            resp = self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        assert_order_cancelled(self, order)
        self.assertEqual(resp.json()["display_status"], "cancelled")
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, qty_before)
        self.assertEqual(stock.reserved_quantity, 0)

        resp2 = self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json")
        self.assertEqual(resp2.status_code, 400)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 0)

    def test_guest_cancel_token_matrix(self):
        order, _, _, stock = _order(user=None, reserved=1)
        qty_before = stock.quantity
        token = issue_guest_access_token(order)
        other, _, _, _ = _order(user=None, reserved=0)
        other_token = issue_guest_access_token(other)

        # без токена
        self.assertEqual(
            self.api.post(
                f"/api/v1/orders/{order.id}/cancel/",
                {"order_number": order.order_number, "phone": order.phone},
                format="json",
            ).status_code,
            403,
        )
        # неверный токен
        self.assertEqual(
            self.api.post(
                f"/api/v1/orders/{order.id}/cancel/",
                {
                    "order_number": order.order_number,
                    "phone": order.phone,
                    "guest_token": "wrong-token",
                },
                format="json",
            ).status_code,
            403,
        )
        # токен другого заказа
        self.assertEqual(
            self.api.post(
                f"/api/v1/orders/{order.id}/cancel/",
                {
                    "order_number": order.order_number,
                    "phone": order.phone,
                    "guest_token": other_token,
                },
                format="json",
            ).status_code,
            403,
        )
        assert_order_not_cancelled(self, order)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 1)

        with patch("apps.orders.tasks.enqueue_order_cancel"):
            ok = self.api.post(
                f"/api/v1/orders/{order.id}/cancel/",
                {
                    "order_number": order.order_number,
                    "phone": order.phone,
                    "guest_token": token,
                },
                format="json",
            )
        self.assertEqual(ok.status_code, 200)
        assert_order_cancelled(self, order)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, qty_before)
        self.assertEqual(stock.reserved_quantity, 0)

        # повтор
        again = self.api.post(
            f"/api/v1/orders/{order.id}/cancel/",
            {
                "order_number": order.order_number,
                "phone": order.phone,
                "guest_token": token,
            },
            format="json",
        )
        self.assertEqual(again.status_code, 400)

    def test_paid_and_ready_and_closed_cannot_customer_cancel(self):
        paid, _, _, stock = _order(
            user=self.user,
            reserved=1,
            payment_type=Order.PAYMENT_ONLINE,
            payment_status=Order.PAYMENT_STATUS_PAID,
        )
        Payment.objects.create(
            order=paid,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PAID,
            amount=paid.total_amount,
            amount_kopecks=10000,
            merchant_order_number="fpb-paid",
        )
        self.assertFalse(customer_may_cancel_order(paid))
        self.api.force_authenticate(user=self.user)
        self.assertEqual(
            self.api.post(f"/api/v1/orders/{paid.id}/cancel/", {}, format="json").status_code,
            400,
        )
        assert_order_not_cancelled(self, paid)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 1)

        ready, _, _, _ = _order(user=self.user, reserved=0, status=Order.STATUS_READY)
        self.assertFalse(customer_may_cancel_order(ready))
        self.assertEqual(
            self.api.post(f"/api/v1/orders/{ready.id}/cancel/", {}, format="json").status_code,
            400,
        )

        done, _, _, _ = _order(user=self.user, reserved=0)
        transition_order_status(
            done,
            Order.STATUS_CLOSED,
            closure_result=Order.CLOSURE_COMPLETED,
        )
        self.assertEqual(
            self.api.post(f"/api/v1/orders/{done.id}/cancel/", {}, format="json").status_code,
            400,
        )

    def test_service_double_cancel_idempotent_multi_item(self):
        product, store, stock = _stocked(qty=20, reserved=5)
        order = Order.objects.create(
            user=self.user,
            full_name="Multi",
            phone=self.user.phone,
            delivery_type=Order.DELIVERY_PICKUP,
            store=store,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("300.00"),
            status=Order.STATUS_NEW,
            consent_personal_data=True,
        )
        for q in (2, 3):
            OrderItem.objects.create(
                order=order,
                product=product,
                product_title=product.title,
                quantity=q,
                price=product.price,
                item_total=product.price * q,
            )
        qty_before = stock.quantity
        with patch("apps.orders.tasks.enqueue_order_cancel") as enq:
            with self.captureOnCommitCallbacks(execute=True):
                cancel_order_and_release_stock(order, reason="first")
                cancel_order_and_release_stock(order, reason="second")
        assert_order_cancelled(self, order)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, qty_before)
        self.assertEqual(stock.reserved_quantity, 0)  # 5 - (2+3)
        self.assertEqual(enq.call_count, 1)

    def test_admin_patch_status_cancelled_alias(self):
        """PATCH status=cancelled должен пройти alias→closed+cancelled (не ChoiceField 400)."""
        from rest_framework_simplejwt.tokens import AccessToken

        from apps.users.admin_mfa import ADMIN_MFA_CLAIM, ADMIN_MFA_CLAIM_VALUE

        order, _, _, stock = _order(user=self.user, reserved=1)
        qty_before = stock.quantity
        staff = CustomUser.objects.create_user(
            phone="79007773333", password="pass12345", is_staff=True
        )
        staff.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
        token = AccessToken.for_user(staff)
        token[ADMIN_MFA_CLAIM] = ADMIN_MFA_CLAIM_VALUE
        self.api.force_authenticate(user=staff, token=token)
        with patch("apps.orders.tasks.enqueue_order_cancel"):
            resp = self.api.patch(
                f"/api/v1/admin/orders/{order.id}/",
                {"status": "cancelled"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        assert_order_cancelled(self, order)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, qty_before)
        self.assertEqual(stock.reserved_quantity, 0)

    def test_series_cancel_releases_matching_stock_only(self):
        product, store, stock_a = _stocked(qty=5, reserved=1, series="SER-A")
        stock_b = Stock.objects.create(
            product=product,
            store=store,
            quantity=5,
            reserved_quantity=2,
            onec_series_id="SER-B",
        )
        order, _, _, _ = _order(
            user=self.user,
            product=product,
            store=store,
            qty=1,
            reserved=1,
            series="SER-A",
        )
        with patch("apps.orders.tasks.enqueue_order_cancel"):
            cancel_order_and_release_stock(order, reason="series")
        stock_a.refresh_from_db()
        stock_b.refresh_from_db()
        self.assertEqual(stock_a.quantity, 5)
        self.assertEqual(stock_a.reserved_quantity, 0)
        self.assertEqual(stock_b.quantity, 5)
        self.assertEqual(stock_b.reserved_quantity, 2)
