"""
Цепочки целостности админки (без браузера): catalog/stock/order/store/user/RBAC.
"""

from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.admin_api.permissions import (
    ALL_ADMIN_GROUPS,
    RINGOO_GROUP_CATALOG,
    RINGOO_GROUP_ORDERS,
    RINGOO_GROUP_STORES,
    RINGOO_GROUP_USERS,
)
from apps.orders.models import Order
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestAdminIntegrityChains(TestCase):
    def setUp(self):
        for name in ALL_ADMIN_GROUPS:
            Group.objects.get_or_create(name=name)
        self.client = APIClient()
        self.superuser = CustomUser.objects.create_superuser(
            "79990000001", password="secretpass123"
        )
        self.staff_orders = CustomUser.objects.create_user(
            "79990000002", password="secretpass123", is_staff=True
        )
        self.staff_orders.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
        self.staff_full = CustomUser.objects.create_user(
            "79990000003", password="secretpass123", is_staff=True
        )
        for name in ALL_ADMIN_GROUPS:
            self.staff_full.groups.add(Group.objects.get(name=name))

        self.category = Category.objects.create(title="Phones", slug="phones", is_active=True)
        self.store = Store.objects.create(
            name="Центр",
            slug="center",
            address="ул. 1",
            city="Москва",
            is_active=True,
            is_warehouse=False,
            onec_warehouse_id="wh-center-1",
        )

    def test_staff_access_returns_groups(self):
        self.client.force_authenticate(user=self.staff_orders)
        r = self.client.get("/api/v1/auth/staff-access/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["staff"])
        self.assertFalse(body["is_superuser"])
        self.assertEqual(body["groups"], [RINGOO_GROUP_ORDERS])

        self.client.force_authenticate(user=self.superuser)
        r = self.client.get("/api/v1/auth/staff-access/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["is_superuser"])
        self.assertEqual(set(r.json()["groups"]), set(ALL_ADMIN_GROUPS))

    def test_product_create_appears_on_public_catalog(self):
        self.client.force_authenticate(user=self.staff_full)
        r = self.client.post(
            "/api/v1/admin/products/create/",
            {
                "title": "iPhone Test",
                "slug": "iphone-test",
                "sku": "SKU-IT-1",
                "category": str(self.category.id),
                "price": "99990.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        product = Product.objects.get(slug="iphone-test")
        product_id = str(product.id)

        self.client.force_authenticate(user=None)
        pub = self.client.get("/api/v1/products/products/iphone-test/")
        self.assertEqual(pub.status_code, 200)
        self.assertEqual(pub.json()["price"], "99990.00")

        Stock.objects.create(
            product=product, store=self.store, quantity=5, reserved_quantity=0
        )
        stock = self.client.get(f"/api/v1/products/products/{product_id}/stock/")
        self.assertEqual(stock.status_code, 200)
        rows = stock.json()["results"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["available_quantity"], 5)

        # Изменение остатка через admin → публичный stock
        stock_id = Stock.objects.get(product=product, store=self.store).id
        self.client.force_authenticate(user=self.staff_full)
        patch = self.client.patch(
            f"/api/v1/admin/stores/stock/{stock_id}/",
            {"quantity": 3},
            format="json",
        )
        self.assertEqual(patch.status_code, 200, patch.content)
        self.client.force_authenticate(user=None)
        stock2 = self.client.get(f"/api/v1/products/products/{product_id}/stock/")
        self.assertEqual(stock2.json()["results"][0]["available_quantity"], 3)

    def test_order_appears_in_admin_and_status_transitions(self):
        product = Product.objects.create(
            title="X",
            slug="x-prod",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )
        Stock.objects.create(product=product, store=self.store, quantity=2)

        buyer = CustomUser.objects.create_user("79990000010", password="secretpass123")
        self.client.force_authenticate(user=buyer)
        created = self.client.post(
            "/api/v1/orders/",
            {
                "full_name": "Buyer",
                "phone": "+79990000010",
                "delivery_type": "pickup",
                "store": str(self.store.id),
                "payment_type": "cash",
                "items": [{"product_id": str(product.id), "quantity": 1, "price": "1.00"}],
                "total_amount": "1.00",
                "consent_personal_data": True,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        order_id = created.json()["id"]

        # SEC-001: чужие заказы — только admin_api, не customer /orders/
        self.client.force_authenticate(user=self.staff_orders)
        customer_listing = self.client.get("/api/v1/orders/")
        self.assertEqual(customer_listing.status_code, 200)
        customer_ids = [o["id"] for o in customer_listing.json()["results"]]
        self.assertNotIn(order_id, customer_ids)

        listing = self.client.get("/api/v1/admin/orders/")
        self.assertEqual(listing.status_code, 200)
        ids = [o["id"] for o in listing.json()["results"]]
        self.assertIn(order_id, ids)

        bad = self.client.patch(
            f"/api/v1/admin/orders/{order_id}/",
            {"status": Order.STATUS_COMPLETED},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)

        ok = self.client.patch(
            f"/api/v1/admin/orders/{order_id}/",
            {"status": Order.STATUS_CONFIRMED},
            format="json",
        )
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(ok.json()["status"], Order.STATUS_CONFIRMED)

    def test_store_warehouse_fields_and_public_exclusion(self):
        self.client.force_authenticate(user=self.staff_full)
        r = self.client.post(
            "/api/v1/admin/stores/create/",
            {
                "name": "Apple Room WH",
                "slug": "apple-room-wh",
                "address": "Склад",
                "city": "Москва",
                "is_active": True,
                "is_warehouse": True,
                "onec_warehouse_id": "wh-apple-room",
                "onec_warehouse_name": "Apple Room",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.json()["is_warehouse"])
        self.assertEqual(r.json()["onec_warehouse_id"], "wh-apple-room")

        self.client.force_authenticate(user=None)
        pub = self.client.get("/api/v1/stores/?is_active=true")
        slugs = [s["slug"] for s in pub.json()["results"]]
        self.assertIn("center", slugs)
        self.assertNotIn("apple-room-wh", slugs)

    def test_blocked_user_cannot_login(self):
        user = CustomUser.objects.create_user("79990000020", password="secretpass123")
        self.client.force_authenticate(user=self.staff_full)
        block = self.client.patch(
            f"/api/v1/admin/users/{user.id}/patch/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(block.status_code, 200, block.content)
        self.client.force_authenticate(user=None)
        login = self.client.post(
            "/api/v1/auth/token/",
            {"phone": "79990000020", "password": "secretpass123"},
            format="json",
        )
        self.assertIn(login.status_code, (400, 401))

    def test_rbac_catalog_forbidden_for_orders_only_staff(self):
        self.client.force_authenticate(user=self.staff_orders)
        r = self.client.get("/api/v1/admin/products/")
        self.assertEqual(r.status_code, 403)
        r2 = self.client.get("/api/v1/admin/orders/")
        self.assertEqual(r2.status_code, 200)

    def test_superuser_assigns_groups(self):
        target = CustomUser.objects.create_user(
            "79990000030", password="secretpass123", is_staff=True
        )
        self.client.force_authenticate(user=self.superuser)
        r = self.client.patch(
            f"/api/v1/admin/users/{target.id}/patch/",
            {"groups": [RINGOO_GROUP_STORES, RINGOO_GROUP_USERS]},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        detail = self.client.get(f"/api/v1/admin/users/{target.id}/")
        self.assertEqual(
            set(detail.json()["groups"]),
            {RINGOO_GROUP_STORES, RINGOO_GROUP_USERS},
        )

        # non-superuser staff_full cannot change groups
        self.client.force_authenticate(user=self.staff_full)
        denied = self.client.patch(
            f"/api/v1/admin/users/{target.id}/patch/",
            {"groups": [RINGOO_GROUP_CATALOG]},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)
