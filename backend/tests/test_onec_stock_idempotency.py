"""BLOCK 1: идемпотентность импорта остатков 1С без qty в ключе."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.products.models import Category, Product
from apps.stores.models import Stock, StockMovement, Store
from apps.stores.stock_ops import (
    apply_onec_stock_upsert,
    build_onec_import_idempotency_key,
)
from integrations.onec.importer import (
    ImportMode,
    plan_catalog_import_from_xml_strings,
)
from tests.onec_plan_apply_helpers import persist_and_apply_for_tests
from tests.onec_test_utils import (
    TEST_OTHER_WH_ID,
    TEST_RETAIL_WH_ID,
    TEST_RETAIL_WH_NAME,
    ensure_confirmed_stores,
)

FOLDERS = '<ПапкиНоменклатуры><Папка code="F1" parentCode="" name="Phones"/>' "</ПапкиНоменклатуры>"


def _products_xml(
    *,
    code: str = "N-1",
    qty: int | str = 5,
    price: str = "100.00",
    sklad: str = TEST_RETAIL_WH_NAME,
    sklad_id: str = TEST_RETAIL_WH_ID,
    series: str = "",
    series_id: str = "",
    extra_rows: str = "",
) -> str:
    series_attrs = ""
    if series or series_id:
        series_attrs = f' series="{series}" seriesID="{series_id}"'
    row = (
        f'<Товар code="{code}" parentCode="F1" name="Phone" '
        f'price="{price}" quantity="{qty}" sklad="{sklad}" skladID="{sklad_id}"'
        f"{series_attrs}/>"
    )
    return f"<Товары>{row}{extra_rows}</Товары>"


class OneCStockIdempotencyKeyTests(TestCase):
    def test_key_is_stable_and_under_128_without_qty(self):
        key_a = build_onec_import_idempotency_key("run-1", "prod-1", "store-1", "series-1")
        key_b = build_onec_import_idempotency_key("run-1", "prod-1", "store-1", "series-1")
        key_other_qty_same_dims = build_onec_import_idempotency_key("run-1", "prod-1", "store-1", "series-1")
        self.assertEqual(key_a, key_b)
        self.assertEqual(key_a, key_other_qty_same_dims)
        self.assertTrue(key_a.startswith("onec:"))
        self.assertEqual(len(key_a), 5 + 64)
        self.assertLessEqual(len(key_a), 128)

    def test_key_differs_by_run_series_store(self):
        base = build_onec_import_idempotency_key("r1", "p", "s", "ser")
        self.assertNotEqual(base, build_onec_import_idempotency_key("r2", "p", "s", "ser"))
        self.assertNotEqual(base, build_onec_import_idempotency_key("r1", "p", "s", "ser2"))
        self.assertNotEqual(base, build_onec_import_idempotency_key("r1", "p", "s2", "ser"))

    def test_long_series_id_does_not_truncate_or_collide(self):
        series_64 = "s" * 64
        key5 = build_onec_import_idempotency_key("run-x", "p", "s", series_64)
        # Количество не входит в ключ — отдельный run даёт другой ключ
        key_other_run = build_onec_import_idempotency_key("run-y", "p", "s", series_64)
        self.assertEqual(len(key5), 69)
        self.assertNotEqual(key5, key_other_run)
        with self.assertRaises(ValueError):
            apply_onec_stock_upsert(
                product_id="p",
                store_id="s",
                series_id=series_64,
                series_name="IMEI",
                quantity=1,
                idempotency_key="x" * 129,
            )


class OneCStockUpsertOscillationTests(TestCase):
    def setUp(self):
        stores = ensure_confirmed_stores()
        cat = Category.objects.create(title="C", slug="idem-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="idem-p",
            sku="N-1",
            onec_code="N-1",
            price=Decimal("100.00"),
            category=cat,
            is_active=True,
        )
        self.store = stores[TEST_RETAIL_WH_ID]
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=0,
            reserved_quantity=2,
            onec_series_id="",
        )

    def test_oscillation_5_8_5_applies_each_new_run(self):
        for qty, run in ((5, "run-a"), (8, "run-b"), (5, "run-c")):
            _row, applied = apply_onec_stock_upsert(
                product_id=self.product.pk,
                store_id=self.store.pk,
                series_id="",
                series_name="",
                quantity=qty,
                run_id=run,
            )
            self.assertTrue(applied)
            self.stock.refresh_from_db()
            self.assertEqual(self.stock.quantity, qty)
            self.assertEqual(self.stock.reserved_quantity, 2)

        self.assertEqual(
            StockMovement.objects.filter(operation=StockMovement.OP_RECONCILIATION, success=True).count(),
            3,
        )

    def test_same_run_repeated_is_idempotent(self):
        _row, applied1 = apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="",
            series_name="",
            quantity=5,
            run_id="same-run",
        )
        _row, applied2 = apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="",
            series_name="",
            quantity=5,
            run_id="same-run",
        )
        self.assertTrue(applied1)
        self.assertFalse(applied2)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 2)
        self.assertEqual(
            StockMovement.objects.filter(operation=StockMovement.OP_RECONCILIATION).count(),
            1,
        )

    def test_failed_prior_movement_allows_retry_same_key(self):
        """ONEC-024: success=False с тем же ключом не блокирует повторный apply."""
        key = build_onec_import_idempotency_key("retry-run", self.product.pk, self.store.pk, "")
        StockMovement.objects.create(
            operation=StockMovement.OP_RECONCILIATION,
            idempotency_key=key,
            quantity=0,
            product_id=self.product.pk,
            store_id=self.store.pk,
            success=False,
            error_message="simulated_failure",
        )
        _row, applied = apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="",
            series_name="",
            quantity=4,
            run_id="retry-run",
        )
        self.assertTrue(applied)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 4)
        self.assertEqual(self.stock.reserved_quantity, 2)
        ok = StockMovement.objects.get(idempotency_key=key)
        self.assertTrue(ok.success)

    def test_new_run_same_quantity_applies_again(self):
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="",
            series_name="",
            quantity=5,
            run_id="run-1",
        )
        # Сменим остаток вручную, чтобы увидеть, что новый run снова пишет 5
        self.stock.quantity = 99
        self.stock.save(update_fields=["quantity"])
        _row, applied = apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="",
            series_name="",
            quantity=5,
            run_id="run-2",
        )
        self.assertTrue(applied)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(
            StockMovement.objects.filter(operation=StockMovement.OP_RECONCILIATION).count(),
            2,
        )

    def test_one_zero_one_oscillation(self):
        for qty, run in ((1, "r1"), (0, "r2"), (1, "r3")):
            apply_onec_stock_upsert(
                product_id=self.product.pk,
                store_id=self.store.pk,
                series_id="",
                series_name="",
                quantity=qty,
                run_id=run,
            )
            self.stock.refresh_from_db()
            self.assertEqual(self.stock.quantity, qty)
            self.assertEqual(self.stock.reserved_quantity, 2)

    def test_long_series_independent_and_reserved_preserved(self):
        series_64 = "S" * 64
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id=series_64,
            series_name="IMEI-LONG",
            quantity=1,
            run_id="ser-run-1",
        )
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id=series_64,
            series_name="IMEI-LONG",
            quantity=0,
            run_id="ser-run-2",
        )
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id=series_64,
            series_name="IMEI-LONG",
            quantity=1,
            run_id="ser-run-3",
        )
        serial = Stock.objects.get(product=self.product, store=self.store, onec_series_id=series_64)
        self.assertEqual(serial.quantity, 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 0)  # blank-series row untouched qty
        self.assertEqual(self.stock.reserved_quantity, 2)

    def test_different_series_and_stores_independent(self):
        store2 = Store.objects.get(onec_warehouse_id=TEST_OTHER_WH_ID)
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="ser-A",
            series_name="A",
            quantity=3,
            run_id="multi-1",
        )
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="ser-B",
            series_name="B",
            quantity=7,
            run_id="multi-1",
        )
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=store2.pk,
            series_id="ser-A",
            series_name="A",
            quantity=9,
            run_id="multi-1",
        )
        a = Stock.objects.get(product=self.product, store=self.store, onec_series_id="ser-A")
        b = Stock.objects.get(product=self.product, store=self.store, onec_series_id="ser-B")
        c = Stock.objects.get(product=self.product, store=store2, onec_series_id="ser-A")
        self.assertEqual(a.quantity, 3)
        self.assertEqual(b.quantity, 7)
        self.assertEqual(c.quantity, 9)


class OneCCatalogPlanReapplyTests(TestCase):
    def setUp(self):
        stores = ensure_confirmed_stores()
        self.category = Category.objects.create(title="Phones", slug="phones-idem", onec_code="F1")
        self.product = Product.objects.create(
            title="Phone",
            slug="phone-idem",
            sku="N-1",
            onec_code="N-1",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )
        self.store = stores[TEST_RETAIL_WH_ID]
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=0,
            reserved_quantity=3,
        )

    def _apply_qty(self, qty: int):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _products_xml(qty=qty),
            mode=ImportMode.APPLY,
        )
        self.assertTrue(plan.apply_allowed, plan.apply_blockers)
        result = persist_and_apply_for_tests(plan)
        return plan, result

    def test_plan_oscillation_and_reapply(self):
        plan5, r1 = self._apply_qty(5)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 3)
        self.assertEqual(r1["stocks_upserted"], 1)
        self.assertTrue(plan5.run_id)

        # Повтор того же плана — без нового движения
        r1b = persist_and_apply_for_tests(plan5)
        self.assertEqual(r1b["stocks_upserted"], 0)
        self.assertEqual(r1b["stocks_skipped_idempotent"], 1)
        self.assertEqual(
            StockMovement.objects.filter(operation=StockMovement.OP_RECONCILIATION, success=True).count(),
            1,
        )

        plan8, r2 = self._apply_qty(8)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.assertNotEqual(plan5.run_id, plan8.run_id)
        self.assertEqual(r2["stocks_upserted"], 1)

        plan5b, r3 = self._apply_qty(5)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 3)
        self.assertNotEqual(plan5.run_id, plan5b.run_id)
        self.assertEqual(r3["stocks_upserted"], 1)
        self.assertEqual(
            StockMovement.objects.filter(operation=StockMovement.OP_RECONCILIATION, success=True).count(),
            3,
        )

    def test_new_plan_same_quantity_writes_again(self):
        plan_a, _ = self._apply_qty(5)
        self.stock.quantity = 50
        self.stock.save(update_fields=["quantity"])
        plan_b, result = self._apply_qty(5)
        self.assertNotEqual(plan_a.run_id, plan_b.run_id)
        self.assertEqual(result["stocks_upserted"], 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(self.stock.reserved_quantity, 3)
