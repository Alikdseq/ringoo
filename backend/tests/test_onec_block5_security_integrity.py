"""
BLOCK 5 — безопасность и целостность складских данных.

ONEC-022: Stock Django Admin / Admin API
ONEC-012: публичный StockListView
ONEC-023: удаление Product без потери Stock/резервов
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.admin.sites import site as admin_site
from django.contrib.auth.models import Group
from django.db.models import ProtectedError
from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.admin_api.permissions import RINGOO_GROUP_CATALOG, RINGOO_GROUP_STORES
from apps.products.admin import ProductAdmin
from apps.products.models import Category, Product
from apps.products.services.lifecycle import (
    product_hard_delete_blocked,
    safe_delete_or_archive_product,
)
from apps.stores.admin import StockAdmin, StockInline
from apps.stores.models import Stock, StockMovement, Store
from apps.users.models import CustomUser


class Block5FixturesMixin:
    def _setup_catalog(self):
        self.client = APIClient()
        self.category = Category.objects.create(title="Cat", slug="cat-b5")
        self.store = Store.objects.create(
            name="Retail",
            slug="retail-b5",
            address="A",
            city="Москва",
            is_active=True,
            onec_warehouse_id="wh-retail-b5",
        )
        self.warehouse = Store.objects.create(
            name="Склад",
            slug="sklad-b5",
            address="B",
            city="Москва",
            is_active=True,
            is_warehouse=True,
            onec_warehouse_id="wh-sklad-b5",
        )
        self.inactive_store = Store.objects.create(
            name="Closed",
            slug="closed-b5",
            address="C",
            city="Москва",
            is_active=False,
            onec_warehouse_id="wh-closed-b5",
        )
        self.product = Product.objects.create(
            title="Phone",
            slug="phone-b5",
            price=Decimal("1000.00"),
            category=self.category,
            is_active=True,
            onec_code="N-B5-1",
        )
        self.local_product = Product.objects.create(
            title="Local",
            slug="local-b5",
            price=Decimal("500.00"),
            category=self.category,
            is_active=True,
        )
        Group.objects.get_or_create(name=RINGOO_GROUP_STORES)
        Group.objects.get_or_create(name=RINGOO_GROUP_CATALOG)
        self.staff = CustomUser.objects.create_user(
            "79990005555",
            password="staffpass123",
            is_staff=True,
        )
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_STORES))
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_CATALOG))
        self.buyer = CustomUser.objects.create_user(
            "79990006666",
            password="userpass123",
        )


class TestOnec022StockAdminProtection(Block5FixturesMixin, TestCase):
    def setUp(self):
        self._setup_catalog()
        self.stock = Stock.objects.create(
            product=self.local_product,
            store=self.store,
            quantity=10,
            reserved_quantity=2,
        )
        self.factory = RequestFactory()
        self.stock_admin = StockAdmin(Stock, admin_site)

    def test_django_admin_cannot_add_or_delete_stock(self):
        request = self.factory.get("/admin/")
        request.user = self.staff
        self.assertFalse(self.stock_admin.has_add_permission(request))
        self.assertFalse(self.stock_admin.has_delete_permission(request, self.stock))

    def test_stock_inline_readonly_no_add_delete(self):
        inline = StockInline(Store, admin_site)
        request = self.factory.get("/admin/")
        request.user = self.staff
        self.assertFalse(inline.has_add_permission(request, self.store))
        self.assertFalse(inline.can_delete)
        self.assertEqual(set(inline.readonly_fields), set(inline.fields))

    def test_admin_api_blocks_reserved_patch(self):
        self.client.force_authenticate(user=self.staff)
        r = self.client.patch(
            f"/api/v1/admin/stores/stock/{self.stock.pk}/",
            {"reserved_quantity": 0},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(r.json().get("code"), "reserved_quantity_readonly")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, 2)

    def test_admin_api_quantity_correction_writes_movement(self):
        self.client.force_authenticate(user=self.staff)
        before = StockMovement.objects.count()
        r = self.client.patch(
            f"/api/v1/admin/stores/stock/{self.stock.pk}/",
            {"quantity": 8},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.assertEqual(self.stock.reserved_quantity, 2)
        self.assertEqual(StockMovement.objects.count(), before + 1)
        mov = StockMovement.objects.order_by("-created_at").first()
        self.assertEqual(mov.operation, StockMovement.OP_CORRECTION)

    def test_admin_api_blocks_onec_quantity_patch(self):
        onec_stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            reserved_quantity=0,
        )
        self.client.force_authenticate(user=self.staff)
        r = self.client.patch(
            f"/api/v1/admin/stores/stock/{onec_stock.pk}/",
            {"quantity": 1},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(r.json().get("code"), "onec_managed_stock_readonly")


class TestOnec012StockListViewAccess(Block5FixturesMixin, TestCase):
    def setUp(self):
        self._setup_catalog()
        Stock.objects.create(
            product=self.product,
            store=self.store,
            onec_series_id="S1",
            quantity=2,
            reserved_quantity=1,
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            onec_series_id="S2",
            quantity=3,
            reserved_quantity=0,
        )
        Stock.objects.create(
            product=self.product,
            store=self.warehouse,
            quantity=7,
            reserved_quantity=0,
        )
        inactive_product = Product.objects.create(
            title="Hidden",
            slug="hidden-b5",
            price=Decimal("10"),
            category=self.category,
            is_active=False,
        )
        Stock.objects.create(
            product=inactive_product,
            store=self.store,
            quantity=99,
            reserved_quantity=0,
        )
        Stock.objects.create(
            product=self.product,
            store=self.inactive_store,
            quantity=50,
            reserved_quantity=0,
        )

    def test_anonymous_store_stock_aggregated_no_reserved(self):
        url = f"/api/v1/stores/{self.store.pk}/stock/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        rows = r.json()["results"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["product"], str(self.product.pk))
        self.assertEqual(row["quantity"], 5)
        self.assertEqual(row["available_quantity"], 4)
        self.assertNotIn("reserved_quantity", row)
        self.assertNotIn("onec_series_id", row)

    def test_authenticated_same_public_payload(self):
        self.client.force_authenticate(user=self.buyer)
        r = self.client.get(f"/api/v1/stores/{self.store.pk}/stock/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 1)

    def test_admin_public_endpoint_same_fields(self):
        self.client.force_authenticate(user=self.staff)
        r = self.client.get(f"/api/v1/stores/{self.store.pk}/stock/")
        self.assertEqual(r.status_code, 200)
        row = r.json()["results"][0]
        self.assertNotIn("reserved_quantity", row)

    def test_warehouse_store_stock_public(self):
        r = self.client.get(f"/api/v1/stores/{self.warehouse.pk}/stock/")
        self.assertEqual(r.status_code, 200)
        rows = r.json()["results"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 7)
        self.assertEqual(rows[0]["available_quantity"], 7)

    def test_inactive_store_returns_404(self):
        r = self.client.get(f"/api/v1/stores/{self.inactive_store.pk}/stock/")
        self.assertEqual(r.status_code, 404)

    def test_admin_stock_list_exposes_reserved_for_staff(self):
        self.client.force_authenticate(user=self.staff)
        r = self.client.get(
            f"/api/v1/admin/stores/stock/?store={self.store.pk}&product={self.product.pk}"
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        results = data.get("results", data)
        self.assertGreaterEqual(len(results), 2)
        self.assertIn("reserved_quantity", results[0])


class TestOnec023ProductDeleteIntegrity(Block5FixturesMixin, TestCase):
    def setUp(self):
        self._setup_catalog()
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=4,
            reserved_quantity=1,
        )

    def test_hard_delete_blocked_when_stock_and_reserves(self):
        blocked, reason = product_hard_delete_blocked(self.product)
        self.assertTrue(blocked)
        self.assertIn("резерв", reason.lower())

    def test_db_protect_prevents_cascade(self):
        with self.assertRaises(ProtectedError):
            self.product.delete()
        self.assertTrue(Stock.objects.filter(pk=self.stock.pk).exists())
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, 1)

    def test_admin_delete_deactivates_and_keeps_stock(self):
        self.client.force_authenticate(user=self.staff)
        r = self.client.delete(f"/api/v1/admin/products/{self.product.pk}/patch/")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body.get("action"), "deactivated")
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 4)
        self.assertEqual(self.stock.reserved_quantity, 1)

    def test_second_delete_blocked_while_stock_exists(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])
        self.client.force_authenticate(user=self.staff)
        r = self.client.delete(f"/api/v1/admin/products/{self.product.pk}/patch/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(r.json().get("code"), "product_delete_blocked")
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_local_empty_product_hard_delete(self):
        empty = Product.objects.create(
            title="Empty",
            slug="empty-b5",
            price=Decimal("1"),
            category=self.category,
            is_active=False,
        )
        decision = safe_delete_or_archive_product(empty)
        self.assertEqual(decision.action, "deleted")
        self.assertFalse(Product.objects.filter(pk=empty.pk).exists())

    def test_django_admin_delete_permission_denied_with_stock(self):
        pa = ProductAdmin(Product, admin_site)
        request = RequestFactory().get("/admin/")
        request.user = self.staff
        self.assertFalse(pa.has_delete_permission(request, self.product))
