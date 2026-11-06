"""INT-001/002: единый FSM статусов заказа."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.orders.admin import OrderAdmin
from apps.orders.models import Order, OrderItem
from apps.orders.services.transitions import (
    OrderTransitionError,
    transition_order_status,
)
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store


User = get_user_model()


def _order(status=Order.STATUS_NEW):
    cat = Category.objects.create(title="C", slug=f"fsm-{Category.objects.count()}")
    product = Product.objects.create(
        title="P",
        slug=f"fsmp-{Product.objects.count()}",
        price=Decimal("100.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"fsms-{Store.objects.count()}", address="a", city="c"
    )
    Stock.objects.create(product=product, store=store, quantity=5, reserved_quantity=1)
    order = Order.objects.create(
        full_name="A",
        phone="79001112233",
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=Order.PAYMENT_CASH,
        status=status,
        total_amount=Decimal("100.00"),
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=1,
        price=Decimal("100.00"),
        item_total=Decimal("100.00"),
    )
    return order


class OrderFsmTests(TestCase):
    def test_allowed_new_to_confirmed(self):
        order = _order()
        locked = transition_order_status(order, Order.STATUS_CONFIRMED, reason="t")
        self.assertEqual(locked.status, Order.STATUS_CONFIRMED)

    def test_idempotent(self):
        order = _order(status=Order.STATUS_CONFIRMED)
        locked = transition_order_status(order, Order.STATUS_CONFIRMED, reason="t")
        self.assertEqual(locked.status, Order.STATUS_CONFIRMED)

    def test_forbidden_cancelled_to_confirmed(self):
        order = _order(status=Order.STATUS_CANCELLED)
        with self.assertRaises(OrderTransitionError):
            transition_order_status(order, Order.STATUS_CONFIRMED, reason="t")

    def test_bulk_admin_skips_cancelled(self):
        staff = User.objects.create_superuser(
            phone="79009998877",
            email="admin-fsm@example.com",
            password="x",
        )
        cancelled = _order(status=Order.STATUS_CANCELLED)
        fresh = _order(status=Order.STATUS_NEW)
        admin = OrderAdmin(Order, AdminSite())
        req = RequestFactory().post("/")
        req.user = staff
        # Django message middleware stub
        from django.contrib.messages.storage.fallback import FallbackStorage

        setattr(req, "session", "session")
        messages = FallbackStorage(req)
        setattr(req, "_messages", messages)
        admin.action_set_status_confirmed(
            req, Order.objects.filter(pk__in=[cancelled.pk, fresh.pk])
        )
        cancelled.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(cancelled.status, Order.STATUS_CANCELLED)
        self.assertEqual(fresh.status, Order.STATUS_CONFIRMED)
