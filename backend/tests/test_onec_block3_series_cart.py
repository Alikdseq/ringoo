"""BLOCK 3: серии, корзина, агрегация наличия, reserved>qty, точка «Склад»."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.stores.stock_ops import apply_onec_stock_upsert, release_at_store, reserve_at_store
from integrations.onec.importer import (
    ImportMode,
    apply_catalog_import,
    diagnose_reserved_over_quantity,
    plan_catalog_import_from_xml_strings,
)
from integrations.onec.orders import InsufficientStockAtStore, plan_and_reserve_at_store
from tests.onec_test_utils import (
    TEST_RETAIL_WH_ID,
    TEST_RETAIL_WH_NAME,
    TEST_TECH_WH_ID,
    ensure_confirmed_stores,
)

FOLDERS = '<ПапкиНоменклатуры><Папка code="F1" parentCode="" name="Phones"/>' "</ПапкиНоменклатуры>"


class MultiSeriesCartTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat = Category.objects.create(title="C", slug="b3-c")
        self.store = Store.objects.create(
            name="M",
            slug="b3-store",
            address="A",
            city="City",
            is_active=True,
            is_warehouse=False,
        )
        self.product = Product.objects.create(
            title="P",
            slug="b3-p",
            price=Decimal("100"),
            category=self.cat,
            is_active=True,
            onec_code="B3-1",
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=1,
            reserved_quantity=0,
            onec_series_id="ser-1",
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=1,
            reserved_quantity=0,
            onec_series_id="ser-2",
        )

    def test_cart_add_with_two_series(self):
        resp = self.client.post(
            "/api/v1/cart/items/",
            {
                "product": str(self.product.pk),
                "quantity": 1,
                "store": str(self.store.pk),
            },
            format="json",
        )
        self.assertIn(resp.status_code, (200, 201), resp.content)

    def test_cart_increment_uses_sum_of_series(self):
        url = "/api/v1/cart/items/"
        self.client.post(
            url,
            {
                "product": str(self.product.pk),
                "quantity": 1,
                "store": str(self.store.pk),
            },
            format="json",
        )
        resp = self.client.post(
            url,
            {
                "product": str(self.product.pk),
                "quantity": 1,
                "store": str(self.store.pk),
            },
            format="json",
        )
        self.assertIn(resp.status_code, (200, 201), resp.content)
        self.assertEqual(resp.json()["items"][0]["quantity"], 2)

    def test_cart_rejects_when_sum_insufficient(self):
        resp = self.client.post(
            "/api/v1/cart/items/",
            {
                "product": str(self.product.pk),
                "quantity": 3,
                "store": str(self.store.pk),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_available_quantity_retail_sums_series(self):
        self.assertEqual(
            Stock.available_quantity_retail(self.product.pk, store_id=self.store.pk),
            2,
        )


class SerialBlankReserveTests(TransactionTestCase):
    def setUp(self):
        self.cat = Category.objects.create(title="C", slug="b3-res-c")
        self.store = Store.objects.create(name="M", slug="b3-res", address="A", city="C", is_active=True)
        self.product = Product.objects.create(
            title="P",
            slug="b3-res-p",
            price=Decimal("10"),
            category=self.cat,
            is_active=True,
            onec_code="B3-RES",
        )

    def test_zero_serial_plus_blank_uses_blank(self):
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=0,
            reserved_quantity=0,
            onec_series_id="dead-ser",
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=3,
            reserved_quantity=0,
            onec_series_id="",
        )
        lines = plan_and_reserve_at_store(
            product=self.product,
            quantity=2,
            price=Decimal("10"),
            store_id=self.store.pk,
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["onec_series_id"], "")
        self.assertEqual(lines[0]["quantity"], 2)
        blank = Stock.objects.get(product=self.product, store=self.store, onec_series_id="")
        self.assertEqual(blank.reserved_quantity, 2)

    def test_multiple_positive_series_reserved(self):
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=1,
            onec_series_id="a",
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=1,
            onec_series_id="b",
        )
        lines = plan_and_reserve_at_store(
            product=self.product,
            quantity=2,
            price=Decimal("10"),
            store_id=self.store.pk,
        )
        self.assertEqual(len(lines), 2)
        self.assertEqual({ln["onec_series_id"] for ln in lines}, {"a", "b"})

    def test_serial_then_blank_remainder(self):
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=1,
            onec_series_id="only",
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            onec_series_id="",
        )
        lines = plan_and_reserve_at_store(
            product=self.product,
            quantity=3,
            price=Decimal("10"),
            store_id=self.store.pk,
        )
        serial_lines = [ln for ln in lines if ln["onec_series_id"]]
        blank_lines = [ln for ln in lines if not ln["onec_series_id"]]
        self.assertEqual(len(serial_lines), 1)
        self.assertEqual(blank_lines[0]["quantity"], 2)

    def test_release_idempotent_no_double(self):
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            reserved_quantity=0,
            onec_series_id="",
        )
        ok = reserve_at_store(
            self.product.pk,
            self.store.pk,
            2,
            idempotency_key="b3-res-1",
        )
        self.assertTrue(ok)
        ok2 = reserve_at_store(
            self.product.pk,
            self.store.pk,
            2,
            idempotency_key="b3-res-1",
        )
        self.assertTrue(ok2)
        row = Stock.objects.get(product=self.product, store=self.store, onec_series_id="")
        self.assertEqual(row.reserved_quantity, 2)
        release_at_store(
            self.product.pk,
            self.store.pk,
            2,
            idempotency_key="b3-rel-1",
        )
        release_at_store(
            self.product.pk,
            self.store.pk,
            2,
            idempotency_key="b3-rel-1",
        )
        row.refresh_from_db()
        self.assertEqual(row.reserved_quantity, 0)

    def test_insufficient_raises(self):
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=1,
            onec_series_id="x",
        )
        with self.assertRaises(InsufficientStockAtStore):
            plan_and_reserve_at_store(
                product=self.product,
                quantity=2,
                price=Decimal("10"),
                store_id=self.store.pk,
            )


class AggregationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat = Category.objects.create(title="C", slug="b3-agg-c")
        self.store = Store.objects.create(name="M", slug="b3-agg", address="A", city="City", is_active=True)
        self.store2 = Store.objects.create(name="M2", slug="b3-agg2", address="B", city="City", is_active=True)
        self.product = Product.objects.create(
            title="P",
            slug="b3-agg-p",
            price=Decimal("10"),
            category=self.cat,
            is_active=True,
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=2,
            reserved_quantity=1,
            onec_series_id="s1",
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=3,
            reserved_quantity=0,
            onec_series_id="s2",
        )
        Stock.objects.create(
            product=self.product,
            store=self.store2,
            quantity=1,
            onec_series_id="s3",
        )

    def test_product_stock_api_one_row_per_store(self):
        url = reverse("api_v1:products:product-stock", kwargs={"pk": self.product.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        by_store = {r["store"]: r for r in results}
        self.assertEqual(len(by_store), 2)
        self.assertEqual(by_store[str(self.store.pk)]["quantity"], 5)
        self.assertEqual(by_store[str(self.store.pk)]["available_quantity"], 4)
        self.assertEqual(by_store[str(self.store2.pk)]["available_quantity"], 1)

    def test_detail_serializer_aggregates(self):
        from apps.products.serializers import ProductDetailSerializer

        data = ProductDetailSerializer(self.product).data
        by_store = {r["store"]: r for r in data["stock"]}
        self.assertEqual(len(by_store), 2)
        self.assertEqual(by_store[str(self.store.pk)]["available_quantity"], 4)

    def test_inactive_store_excluded(self):
        self.store2.is_active = False
        self.store2.save(update_fields=["is_active"])
        rows = Stock.aggregated_public_stock_for_product(self.product.pk)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["store"], str(self.store.pk))
        self.assertEqual(Stock.available_quantity_retail(self.product.pk), 4)


class WarehousePointTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.tech = self.stores[TEST_TECH_WH_ID]
        self.cat = Category.objects.create(title="C", slug="b3-wh-c")
        self.product = Product.objects.create(
            title="P",
            slug="b3-wh-p",
            price=Decimal("10"),
            category=self.cat,
            is_active=True,
        )
        self.client = APIClient()

    def test_warehouse_counts_and_orderable(self):
        Stock.objects.create(product=self.product, store=self.tech, quantity=4, reserved_quantity=0)
        self.assertTrue(self.tech.is_warehouse)
        self.assertTrue(self.tech.is_active)
        self.assertEqual(Stock.available_quantity_retail(self.product.pk), 4)
        resp = self.client.post(
            "/api/v1/cart/items/",
            {
                "product": str(self.product.pk),
                "quantity": 1,
                "store": str(self.tech.pk),
            },
            format="json",
        )
        self.assertIn(resp.status_code, (200, 201))
        from apps.orders.serializers import OrderCreateSerializer

        s = OrderCreateSerializer(
            data={
                "full_name": "T",
                "phone": "+7",
                "delivery_type": "pickup",
                "payment_type": "cash",
                "store": str(self.tech.pk),
                "items": [
                    {
                        "product_id": str(self.product.pk),
                        "quantity": 1,
                        "price": "10.00",
                    }
                ],
                "total_amount": Decimal("10.00"),
                "consent_personal_data": True,
            }
        )
        self.assertTrue(s.is_valid(), s.errors)


class SeriesIdImportTests(TestCase):
    def setUp(self):
        ensure_confirmed_stores()
        Category.objects.create(title="C", slug="b3-ser-c", onec_code="F1")
        Product.objects.create(
            title="P",
            slug="b3-ser-p",
            onec_code="N-SER",
            price=Decimal("10"),
            category=Category.objects.get(onec_code="F1"),
            is_active=True,
        )

    def test_series_without_series_id_blocks_apply(self):
        products = (
            "<Товары>"
            f'<Товар code="N-SER" parentCode="F1" name="Phone" price="10" '
            f'quantity="1" sklad="{TEST_RETAIL_WH_NAME}" '
            f'skladID="{TEST_RETAIL_WH_ID}" series="IMEI-ONLY"/>'
            "</Товары>"
        )
        plan = plan_catalog_import_from_xml_strings(FOLDERS, products, mode=ImportMode.DRY_RUN)
        self.assertFalse(plan.apply_allowed)
        self.assertTrue(any(b["type"] == "series_missing_id" for b in plan.apply_blockers))

    def test_normal_product_without_series_ok(self):
        products = (
            "<Товары>"
            f'<Товар code="N-SER" parentCode="F1" name="Phone" price="10" '
            f'quantity="2" sklad="{TEST_RETAIL_WH_NAME}" '
            f'skladID="{TEST_RETAIL_WH_ID}"/>'
            "</Товары>"
        )
        plan = plan_catalog_import_from_xml_strings(FOLDERS, products, mode=ImportMode.APPLY)
        self.assertTrue(plan.apply_allowed, plan.apply_blockers)
        apply_catalog_import(plan)
        store = Store.objects.get(onec_warehouse_id=TEST_RETAIL_WH_ID)
        stock = Stock.objects.get(product__onec_code="N-SER", store=store, onec_series_id="")
        self.assertEqual(stock.quantity, 2)


class ReservedOverQuantityTests(TestCase):
    def setUp(self):
        ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="b3-ov-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="b3-ov-p",
            onec_code="N-OV",
            price=Decimal("10"),
            category=self.cat,
            is_active=True,
        )
        self.store = Store.objects.get(onec_warehouse_id=TEST_RETAIL_WH_ID)
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            reserved_quantity=3,
            onec_series_id="",
        )

    def test_import_qty_below_reserved_keeps_reserve(self):
        products = (
            "<Товары>"
            f'<Товар code="N-OV" parentCode="F1" name="Phone" price="10" '
            f'quantity="1" sklad="{TEST_RETAIL_WH_NAME}" '
            f'skladID="{TEST_RETAIL_WH_ID}"/>'
            "</Товары>"
        )
        plan = plan_catalog_import_from_xml_strings(FOLDERS, products, mode=ImportMode.APPLY)
        self.assertTrue(plan.apply_allowed, plan.apply_blockers)
        result = apply_catalog_import(plan)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 1)
        self.assertEqual(self.stock.reserved_quantity, 3)
        self.assertEqual(self.stock.available_quantity, 0)
        self.assertGreaterEqual(result["reserved_over_quantity_count"], 1)
        report = diagnose_reserved_over_quantity()
        self.assertGreaterEqual(report["anomaly_count"], 1)
        self.assertEqual(report["action"], "report_only")

    def test_restock_restores_availability_without_cutting_reserve(self):
        self.stock.quantity = 1
        self.stock.reserved_quantity = 3
        self.stock.save(update_fields=["quantity", "reserved_quantity"])
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="",
            series_name="",
            quantity=5,
            run_id="restock-run",
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 3)
        self.assertEqual(self.stock.available_quantity, 2)
        report = diagnose_reserved_over_quantity()
        self.assertFalse(any(a["stock_id"] == str(self.stock.pk) for a in report["anomalies"]))
