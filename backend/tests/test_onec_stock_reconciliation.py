"""BLOCK 2 + сверка остатков + публичное наличие + корзина."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from integrations.onec.importer import (
    ImportMode,
    apply_catalog_import,
    plan_catalog_import_from_xml_strings,
)
from integrations.onec.warehouse_map import CONFIRMED_WAREHOUSES, CONFIRMED_WAREHOUSE_IDS
from tests.onec_test_utils import (
    TEST_OTHER_WH_ID,
    TEST_RETAIL_WH_ID,
    TEST_RETAIL_WH_NAME,
    TEST_TECH_WH_ID,
    ensure_confirmed_stores,
)


FOLDERS = (
    '<ПапкиНоменклатуры><Папка code="F1" parentCode="" name="Phones"/>'
    "</ПапкиНоменклатуры>"
)


def _xml(*rows: str) -> str:
    return "<Товары>" + "".join(rows) + "</Товары>"


def _row(
    code: str,
    price: str,
    qty: str | int,
    *,
    name: str = "Phone",
    sklad: str = TEST_RETAIL_WH_NAME,
    sklad_id: str = TEST_RETAIL_WH_ID,
    series: str = "",
    series_id: str = "",
) -> str:
    extra = ""
    if series or series_id:
        extra = f' series="{series}" seriesID="{series_id}"'
    return (
        f'<Товар code="{code}" parentCode="F1" name="{name}" '
        f'price="{price}" quantity="{qty}" sklad="{sklad}" skladID="{sklad_id}"'
        f"{extra}/>"
    )


class WarehouseMappingTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()

    def test_all_nine_confirmed_mapped(self):
        self.assertEqual(len(CONFIRMED_WAREHOUSE_IDS), 9)
        for w in CONFIRMED_WAREHOUSES:
            store = self.stores[w.warehouse_id]
            self.assertEqual(store.onec_warehouse_id, w.warehouse_id)
            self.assertEqual(store.is_warehouse, w.is_warehouse)

    def test_reimport_does_not_create_duplicate_stores(self):
        before = Store.objects.count()
        ensure_confirmed_stores()
        self.assertEqual(Store.objects.count(), before)

    def test_unknown_warehouse_blocks_apply(self):
        Category.objects.create(title="C", slug="c", onec_code="F1")
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(
                _row(
                    "N1",
                    "10",
                    1,
                    sklad="X",
                    sklad_id="00000000-0000-0000-0000-000000000099",
                )
            ),
            mode=ImportMode.DRY_RUN,
        )
        self.assertFalse(plan.apply_allowed)
        types = {b["type"] for b in plan.apply_blockers}
        self.assertIn("unknown_warehouse", types)

    def test_tech_warehouse_flag(self):
        tech = self.stores[TEST_TECH_WH_ID]
        self.assertTrue(tech.is_warehouse)
        self.assertTrue(tech.is_active)


class StockReconciliationTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="rec-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="rec-p",
            sku="N-1",
            onec_code="N-1",
            price=Decimal("100"),
            category=self.cat,
            is_active=True,
        )
        self.store_a = self.stores[TEST_RETAIL_WH_ID]
        self.store_b = self.stores[TEST_OTHER_WH_ID]
        self.stock_a = Stock.objects.create(
            product=self.product,
            store=self.store_a,
            quantity=5,
            reserved_quantity=2,
            onec_series_id="",
        )
        self.stock_b = Stock.objects.create(
            product=self.product,
            store=self.store_b,
            quantity=3,
            reserved_quantity=0,
            onec_series_id="",
        )

    def _apply(self, *rows: str):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS, _xml(*rows), mode=ImportMode.APPLY
        )
        self.assertTrue(plan.apply_allowed, plan.apply_blockers)
        return plan, apply_catalog_import(plan)

    def test_missing_from_snapshot_zeros_old_stock(self):
        # Только склад A с qty=4 → B должен обнулиться
        plan, result = self._apply(_row("N-1", "100", 4))
        self.stock_a.refresh_from_db()
        self.stock_b.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.stock_a.quantity, 4)
        self.assertEqual(self.stock_b.quantity, 0)
        self.assertEqual(self.stock_a.reserved_quantity, 2)
        self.assertTrue(self.product.is_active)
        self.assertGreaterEqual(result["stocks_zeroed"], 1)
        self.assertTrue(any(z.action == "zero" for z in plan.stocks_to_zero))

    def test_product_returns_in_next_snapshot(self):
        self._apply(_row("N-1", "100", 0))  # explicit zero path via upsert if present
        # Полностью отсутствует → zero
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-OTHER", "50", 1, name="Other")),
            mode=ImportMode.APPLY,
        )
        # N-OTHER new needs create - ensure category ok
        Product.objects.create(
            title="Other",
            slug="rec-other",
            onec_code="N-OTHER",
            price=Decimal("50"),
            category=self.cat,
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-OTHER", "50", 1, name="Other")),
            mode=ImportMode.APPLY,
        )
        apply_catalog_import(plan)
        self.stock_a.refresh_from_db()
        self.assertEqual(self.stock_a.quantity, 0)

        self._apply(_row("N-1", "100", 7))
        self.stock_a.refresh_from_db()
        self.assertEqual(self.stock_a.quantity, 7)
        self.assertEqual(self.stock_a.reserved_quantity, 2)

    def test_series_zero_independent(self):
        Stock.objects.create(
            product=self.product,
            store=self.store_a,
            quantity=1,
            reserved_quantity=0,
            onec_series_id="ser-keep",
            onec_series_name="K",
        )
        Stock.objects.create(
            product=self.product,
            store=self.store_a,
            quantity=1,
            reserved_quantity=0,
            onec_series_id="ser-gone",
            onec_series_name="G",
        )
        self._apply(
            _row("N-1", "100", 1, series="K", series_id="ser-keep"),
            _row(
                "N-1",
                "100",
                2,
                sklad="Беслан",
                sklad_id=TEST_OTHER_WH_ID,
            ),
        )
        keep = Stock.objects.get(
            product=self.product, store=self.store_a, onec_series_id="ser-keep"
        )
        gone = Stock.objects.get(
            product=self.product, store=self.store_a, onec_series_id="ser-gone"
        )
        blank = Stock.objects.get(
            product=self.product, store=self.store_a, onec_series_id=""
        )
        self.assertEqual(keep.quantity, 1)
        self.assertEqual(gone.quantity, 0)
        self.assertEqual(blank.quantity, 0)

    def test_empty_warehouse_in_xml_zeros_that_store(self):
        # Склад B отсутствует в XML целиком
        self._apply(_row("N-1", "100", 1))
        self.stock_b.refresh_from_db()
        self.assertEqual(self.stock_b.quantity, 0)

    def test_same_plan_reapply_idempotent(self):
        plan, r1 = self._apply(_row("N-1", "100", 4))
        r2 = apply_catalog_import(plan)
        self.assertEqual(r2["stocks_upserted"], 0)
        self.assertEqual(r2["stocks_zeroed"], 0)
        self.assertGreater(r2["stocks_skipped_idempotent"], 0)

    def test_corrupted_qty_blocks_zero_phase(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-1", "100", "abc")),
            mode=ImportMode.DRY_RUN,
        )
        self.assertFalse(plan.apply_allowed)
        self.assertEqual(plan.stocks_to_zero, [])


class PublicAvailabilityAndCartTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="pub-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="pub-p",
            onec_code="N-PUB",
            price=Decimal("10"),
            category=self.cat,
            is_active=True,
        )
        self.retail = self.stores[TEST_RETAIL_WH_ID]
        self.tech = self.stores[TEST_TECH_WH_ID]
        self.client = APIClient()

    def test_warehouse_stock_makes_public_in_stock(self):
        """Apple Room / «Склад»: is_warehouse — метка, наличие публичное."""
        Stock.objects.create(
            product=self.product,
            store=self.tech,
            quantity=10,
            reserved_quantity=0,
        )
        self.assertEqual(Stock.available_quantity_retail(self.product.pk), 10)
        from apps.products.serializers import ProductListSerializer

        data = ProductListSerializer(self.product).data
        self.assertEqual(data["availability_status"], "in_stock")

    def test_retail_stock_in_stock(self):
        Stock.objects.create(
            product=self.product,
            store=self.retail,
            quantity=3,
            reserved_quantity=1,
        )
        self.assertEqual(Stock.available_quantity_retail(self.product.pk), 2)

    def test_cart_rejects_out_of_stock_without_store(self):
        resp = self.client.post(
            "/api/v1/cart/items/",
            {"product": str(self.product.pk), "quantity": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_cart_allows_warehouse_store(self):
        Stock.objects.create(
            product=self.product, store=self.tech, quantity=5, reserved_quantity=0
        )
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

    def test_cart_allows_retail_stock(self):
        Stock.objects.create(
            product=self.product, store=self.retail, quantity=5, reserved_quantity=0
        )
        resp = self.client.post(
            "/api/v1/cart/items/",
            {"product": str(self.product.pk), "quantity": 1},
            format="json",
        )
        self.assertIn(resp.status_code, (200, 201))

    def test_product_stays_active_after_zero(self):
        Stock.objects.create(
            product=self.product, store=self.retail, quantity=5, reserved_quantity=1
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-OTHER2", "10", 1, name="Other2")),
            mode=ImportMode.APPLY,
        )
        Product.objects.create(
            title="Other2",
            slug="pub-o2",
            onec_code="N-OTHER2",
            price=Decimal("10"),
            category=self.cat,
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-OTHER2", "10", 1, name="Other2")),
            mode=ImportMode.APPLY,
        )
        apply_catalog_import(plan)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)
        stock = Stock.objects.get(product=self.product, store=self.retail)
        self.assertEqual(stock.quantity, 0)
        self.assertEqual(stock.reserved_quantity, 1)

    def test_warehouse_stock_syncs_and_counts_public(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(
                _row(
                    "N-PUB",
                    "10",
                    4,
                    sklad="Склад",
                    sklad_id=TEST_TECH_WH_ID,
                )
            ),
            mode=ImportMode.APPLY,
        )
        self.assertTrue(plan.apply_allowed, plan.apply_blockers)
        apply_catalog_import(plan)
        tech_stock = Stock.objects.get(
            product=self.product, store=self.tech, onec_series_id=""
        )
        self.assertEqual(tech_stock.quantity, 4)
        self.assertEqual(Stock.available_quantity_retail(self.product.pk), 4)
        self.assertTrue(self.tech.is_warehouse)
        self.assertTrue(self.tech.is_active)

    def test_in_stock_filter_includes_warehouse_stock(self):
        from apps.products.catalog_filters import apply_catalog_filters
        from apps.products.models import Product as ProductModel

        Stock.objects.create(
            product=self.product, store=self.tech, quantity=9, reserved_quantity=0
        )
        qs = apply_catalog_filters(
            ProductModel.objects.filter(is_active=True), {"in_stock": "true"}
        )
        self.assertTrue(qs.filter(pk=self.product.pk).exists())

        qs_all = apply_catalog_filters(ProductModel.objects.filter(is_active=True), {})
        self.assertTrue(qs_all.filter(pk=self.product.pk).exists())

    def test_price_blocked_still_updates_existing_stock(self):
        Stock.objects.create(
            product=self.product, store=self.retail, quantity=1, reserved_quantity=0
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-PUB", "", 6)),  # empty price
            mode=ImportMode.APPLY,
        )
        # Пустая цена блокирует карточку, но не existing stock upsert
        upserts = [s for s in plan.stocks if s.action == "upsert"]
        self.assertTrue(upserts)
        apply_catalog_import(plan)
        stock = Stock.objects.get(product=self.product, store=self.retail)
        self.assertEqual(stock.quantity, 6)

    def test_apply_rolls_back_on_mid_error(self):
        from unittest.mock import patch

        Stock.objects.create(
            product=self.product, store=self.retail, quantity=5, reserved_quantity=0
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS, _xml(_row("N-PUB", "10", 2)), mode=ImportMode.APPLY
        )
        self.assertTrue(plan.apply_allowed)
        with patch(
            "apps.stores.stock_ops.apply_onec_stock_upserts_batch",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                apply_catalog_import(plan)
        stock = Stock.objects.get(product=self.product, store=self.retail)
        self.assertEqual(stock.quantity, 5)
