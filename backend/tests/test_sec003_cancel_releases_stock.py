"""
SEC-003: отмена заказа освобождает резерв ровно один раз.
Проверяем reserved_quantity, не только status=cancelled.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.admin_api.permissions import RINGOO_GROUP_ORDERS
from apps.orders.models import Order, OrderItem
from apps.orders.services import cancel_order_and_release_stock
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser


def _reserved_order(*, qty=2, stock_qty=10, reserved=2):
    cat = Category.objects.create(
        title="C", slug=f"sec3-c-{Category.objects.count()}"
    )
    product = Product.objects.create(
        title="P",
        slug=f"sec3-p-{Product.objects.count()}",
        price=Decimal("500.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="Store",
        slug=f"sec3-s-{Store.objects.count()}",
        address="a",
        city="Москва",
        is_active=True,
    )
    stock = Stock.objects.create(
        product=product,
        store=store,
        quantity=stock_qty,
        reserved_quantity=reserved,
        onec_series_id="",
    )
    user = CustomUser.objects.create_user(
        phone=f"79003{100000 + Order.objects.count():06d}",
        password="pass12345",
    )
    order = Order.objects.create(
        user=user,
        full_name="Buyer",
        phone=user.phone,
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=Order.PAYMENT_CASH,
        total_amount=product.price * qty,
        status=Order.STATUS_NEW,
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=qty,
        price=product.price,
        item_total=product.price * qty,
    )
    return order, stock, user


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
class Sec003CancelReleasesStockTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
        self.api = APIClient()

    def test_user_cancel_releases_reserved_once(self):
        order, stock, user = _reserved_order(qty=2, reserved=2)
        self.assertEqual(stock.reserved_quantity, 2)

        self.api.force_authenticate(user=user)
        with patch("apps.orders.tasks.enqueue_order_cancel") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.api.post(
                    f"/api/v1/orders/{order.id}/cancel/", {}, format="json"
                )
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(stock.reserved_quantity, 0)
        enqueue.assert_called_once_with(order.pk)

        # Повторная отмена: статус уже cancelled → 400 на user API
        resp2 = self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json")
        self.assertEqual(resp2.status_code, 400)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 0)

    def test_service_double_cancel_does_not_over_release(self):
        order, stock, _user = _reserved_order(qty=2, reserved=2)
        # Чужой резерв на том же stock (имитация другого заказа)
        stock.reserved_quantity = 5
        stock.save(update_fields=["reserved_quantity"])

        with patch("apps.orders.tasks.enqueue_order_cancel") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                cancel_order_and_release_stock(order, reason="first")
                cancel_order_and_release_stock(order, reason="second")

        stock.refresh_from_db()
        # Сняли только qty=2 один раз → 5-2=3
        self.assertEqual(stock.reserved_quantity, 3)
        self.assertEqual(enqueue.call_count, 1)

    def test_admin_patch_cancelled_releases_reserved(self):
        order, stock, _user = _reserved_order(qty=2, reserved=2)
        staff = CustomUser.objects.create_user(
            phone="79003990001", password="pass12345", is_staff=True
        )
        staff.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
        self.api.force_authenticate(user=staff)

        with patch("apps.orders.tasks.enqueue_order_cancel") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.api.patch(
                    f"/api/v1/admin/orders/{order.id}/",
                    {"status": Order.STATUS_CANCELLED},
                    format="json",
                )
        self.assertEqual(resp.status_code, 200, resp.content)
        order.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(stock.reserved_quantity, 0)
        enqueue.assert_called_once_with(order.pk)

        # Повторный PATCH cancelled — без повторного release / enqueue
        with patch("apps.orders.tasks.enqueue_order_cancel") as enqueue2:
            with self.captureOnCommitCallbacks(execute=True):
                resp2 = self.api.patch(
                    f"/api/v1/admin/orders/{order.id}/",
                    {"status": Order.STATUS_CANCELLED},
                    format="json",
                )
        self.assertEqual(resp2.status_code, 200)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 0)
        enqueue2.assert_not_called()

    def test_admin_forbidden_transition_keeps_reserve(self):
        order, stock, _user = _reserved_order(qty=1, reserved=1)
        order.status = Order.STATUS_COMPLETED
        order.save(update_fields=["status"])
        staff = CustomUser.objects.create_user(
            phone="79003990002", password="pass12345", is_staff=True
        )
        staff.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
        self.api.force_authenticate(user=staff)
        resp = self.api.patch(
            f"/api/v1/admin/orders/{order.id}/",
            {"status": Order.STATUS_CANCELLED},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 1)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_COMPLETED)

    def test_cancel_does_not_delete_order_or_items(self):
        order, stock, user = _reserved_order(qty=1, reserved=1)
        item_id = order.items.first().id
        self.api.force_authenticate(user=user)
        with patch("apps.orders.tasks.enqueue_order_cancel"):
            self.api.post(f"/api/v1/orders/{order.id}/cancel/", {}, format="json")
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
        self.assertTrue(OrderItem.objects.filter(pk=item_id).exists())

    def test_django_admin_save_releases_stock(self):
        order, stock, _user = _reserved_order(qty=2, reserved=2)
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        from apps.orders.admin import OrderAdmin

        rf = RequestFactory()
        request = rf.post("/admin/")
        request.user = CustomUser.objects.create_superuser(
            phone="79003990099", password="pass12345"
        )
        admin_obj = OrderAdmin(Order, AdminSite())
        order.status = Order.STATUS_CANCELLED
        with patch("apps.orders.tasks.enqueue_order_cancel") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                admin_obj.save_model(request, order, form=None, change=True)
        stock.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(stock.reserved_quantity, 0)
        enqueue.assert_called_once()
