"""
SEC-001: staff без admin_api MFA/группы не видит чужие заказы через customer API.
Проверяются list / detail / cancel / pay.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.admin_api.permissions import RINGOO_GROUP_ORDERS
from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.admin_mfa import issue_tokens_with_admin_mfa
from apps.users.models import CustomUser


def _make_order(*, user=None, phone="79001112233", full_name="Buyer"):
    cat = Category.objects.create(title="C", slug=f"c-{phone[-4:]}-{Order.objects.count()}")
    product = Product.objects.create(
        title="Phone",
        slug=f"p-{phone[-4:]}-{Order.objects.count()}",
        price=Decimal("1000.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S",
        slug=f"s-{phone[-4:]}-{Order.objects.count()}",
        address="a",
        city="Москва",
        is_active=True,
    )
    Stock.objects.create(product=product, store=store, quantity=5, reserved_quantity=1)
    order = Order.objects.create(
        user=user,
        full_name=full_name,
        phone=phone,
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=Order.PAYMENT_CASH,
        total_amount=Decimal("1000.00"),
        status=Order.STATUS_NEW,
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=1,
        price=product.price,
    )
    return order, product, store


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
    ADMIN_OTP_ENABLED=False,
    SBER_ECOM_ENABLED=False,
    YOOKASSA_ENABLED=False,
)
class Sec001StaffCustomerApiAccessTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
        self.api = APIClient()
        self.owner = CustomUser.objects.create_user(
            phone="79001110001", password="pass12345"
        )
        self.other = CustomUser.objects.create_user(
            phone="79001110002", password="pass12345"
        )
        self.staff_no_group = CustomUser.objects.create_user(
            phone="79001110003", password="pass12345", is_staff=True
        )
        self.staff_with_group = CustomUser.objects.create_user(
            phone="79001110004", password="pass12345", is_staff=True
        )
        self.staff_with_group.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))

        self.owner_order, _, _ = _make_order(user=self.owner, phone=self.owner.phone)
        self.staff_own_order, _, _ = _make_order(
            user=self.staff_no_group, phone=self.staff_no_group.phone, full_name="Staff Own"
        )
        self.guest_order, _, _ = _make_order(user=None, phone="79001119999")

    def test_owner_sees_own_orders_only(self):
        self.api.force_authenticate(user=self.owner)
        resp = self.api.get("/api/v1/orders/")
        self.assertEqual(resp.status_code, 200)
        ids = {o["id"] for o in resp.json()["results"]}
        self.assertIn(str(self.owner_order.id), ids)
        self.assertNotIn(str(self.staff_own_order.id), ids)

    def test_other_user_cannot_see_owner_order_detail(self):
        self.api.force_authenticate(user=self.other)
        resp = self.api.get(f"/api/v1/orders/{self.owner_order.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_staff_without_group_list_excludes_others(self):
        self.api.force_authenticate(user=self.staff_no_group)
        resp = self.api.get("/api/v1/orders/")
        self.assertEqual(resp.status_code, 200)
        ids = {o["id"] for o in resp.json()["results"]}
        self.assertIn(str(self.staff_own_order.id), ids)
        self.assertNotIn(str(self.owner_order.id), ids)
        self.assertNotIn(str(self.guest_order.id), ids)

    def test_staff_without_group_cannot_detail_foreign_order(self):
        self.api.force_authenticate(user=self.staff_no_group)
        resp = self.api.get(f"/api/v1/orders/{self.owner_order.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_staff_without_group_cannot_cancel_foreign_order(self):
        self.api.force_authenticate(user=self.staff_no_group)
        resp = self.api.post(
            f"/api/v1/orders/{self.owner_order.id}/cancel/", {}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        self.owner_order.refresh_from_db()
        self.assertEqual(self.owner_order.status, Order.STATUS_NEW)

    def test_staff_without_group_cannot_pay_foreign_order(self):
        self.api.force_authenticate(user=self.staff_no_group)
        resp = self.api.post(
            f"/api/v1/orders/{self.owner_order.id}/pay/", {}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_staff_can_access_own_order(self):
        self.api.force_authenticate(user=self.staff_no_group)
        resp = self.api.get(f"/api/v1/orders/{self.staff_own_order.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], str(self.staff_own_order.id))

    def test_staff_with_group_sees_foreign_via_admin_api(self):
        self.api.force_authenticate(user=self.staff_with_group)
        listing = self.api.get("/api/v1/admin/orders/")
        self.assertEqual(listing.status_code, 200)
        ids = {o["id"] for o in listing.json()["results"]}
        self.assertIn(str(self.owner_order.id), ids)

        detail = self.api.get(f"/api/v1/admin/orders/{self.owner_order.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["id"], str(self.owner_order.id))

    def test_staff_with_group_still_blocked_on_customer_api(self):
        """Группа admin не открывает customer API для чужих заказов."""
        self.api.force_authenticate(user=self.staff_with_group)
        resp = self.api.get(f"/api/v1/orders/{self.owner_order.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_regular_user_denied_admin_orders(self):
        self.api.force_authenticate(user=self.owner)
        resp = self.api.get("/api/v1/admin/orders/")
        self.assertEqual(resp.status_code, 403)

    def test_guest_track_still_works(self):
        # Без guest_token — только урезанный статус (SEC-006 final).
        limited = self.api.get(
            "/api/v1/orders/track/",
            {
                "order_number": self.guest_order.order_number,
                "phone": self.guest_order.phone,
            },
        )
        self.assertEqual(limited.status_code, 200)
        self.assertTrue(limited.json().get("guest_token_required"))
        self.assertNotIn("id", limited.json())

        from apps.orders.guest_access import issue_guest_access_token

        token = issue_guest_access_token(self.guest_order)
        resp = self.api.get(
            "/api/v1/orders/track/",
            {
                "order_number": self.guest_order.order_number,
                "phone": self.guest_order.phone,
                "guest_token": token,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], str(self.guest_order.id))

    def test_guest_wrong_phone_denied(self):
        resp = self.api.get(
            "/api/v1/orders/track/",
            {
                "order_number": self.guest_order.order_number,
                "phone": "79000000000",
            },
        )
        self.assertEqual(resp.status_code, 404)

    def test_guest_cancel_without_credentials_denied(self):
        resp = self.api.post(
            f"/api/v1/orders/{self.guest_order.id}/cancel/", {}, format="json"
        )
        # SEC-006: без guest_token / legacy credentials — 403
        self.assertEqual(resp.status_code, 403)


@override_settings(
    ADMIN_OTP_ENABLED=True,
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class Sec001StaffMfaAdminAccessTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
        self.api = APIClient()
        self.staff = CustomUser.objects.create_user(
            phone="79001110010", password="pass12345", is_staff=True
        )
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
        self.owner = CustomUser.objects.create_user(
            phone="79001110011", password="pass12345"
        )
        self.order, _, _ = _make_order(user=self.owner, phone=self.owner.phone)

    def test_staff_without_mfa_claim_denied_admin_orders(self):
        refresh = RefreshToken.for_user(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = self.api.get("/api/v1/admin/orders/")
        self.assertEqual(resp.status_code, 403)
        # Customer API тоже не отдаёт чужой заказ
        resp2 = self.api.get(f"/api/v1/orders/{self.order.id}/")
        self.assertEqual(resp2.status_code, 404)

    def test_staff_with_mfa_claim_can_use_admin_orders(self):
        access, _ = issue_tokens_with_admin_mfa(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.api.get("/api/v1/admin/orders/")
        self.assertEqual(resp.status_code, 200)
        ids = {o["id"] for o in resp.json()["results"]}
        self.assertIn(str(self.order.id), ids)
