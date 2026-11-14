"""
BLOCK 6 — измерения производительности (каталог / upsert / synthetic import).

Запускается на локальной test DB. Не использует production-данные.
"""

from __future__ import annotations

import gc
import time
import tracemalloc
from decimal import Decimal

from django.db import connection, transaction
from django.core.cache import cache
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Stock, StockMovement
from apps.stores.stock_ops import apply_onec_stock_upsert
from tests.onec_test_utils import (
    TEST_RETAIL_WH_ID,
    TEST_RETAIL_WH_NAME,
    ensure_confirmed_stores,
)


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


class Block6PerformanceBaselineAndGuardrails(TestCase):
    """
    Фиксирует показатели и guardrail'ы после оптимизаций.
    Baseline «до» задокументирован в docs/audit/BLOCK6_PERFORMANCE_REPORT.md
    (замеры этапа A на том же сценарии).
    """

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        self.stores = ensure_confirmed_stores()
        self.category = Category.objects.create(
            title="PerfCat", slug="perf-cat-b6", is_active=True, onec_code="F-PERF"
        )

    def _seed_catalog(self, n_products: int = 24, stores_n: int = 5, series_n: int = 3):
        store_list = list(self.stores.values())[:stores_n]
        products = []
        for i in range(n_products):
            p = Product.objects.create(
                title=f"Perf Phone {i}",
                slug=f"perf-b6-{i}",
                price=Decimal("19990.00"),
                category=self.category,
                is_active=True,
                onec_code=f"PERF-B6-{i}",
            )
            products.append(p)
            for s in store_list:
                for si in range(series_n):
                    series_id = "" if si == 0 else f"SER-{i}-{si}"
                    Stock.objects.create(
                        product=p,
                        store=s,
                        onec_series_id=series_id,
                        quantity=5,
                        reserved_quantity=1,
                    )
        return products, store_list

    def test_catalog_list_query_budget(self):
        products, _ = self._seed_catalog(24, 5, 3)
        # cold cache
        with CaptureQueriesContext(connection) as ctx:
            t0 = time.perf_counter()
            r = self.client.get("/api/v1/products/products/?page_size=24")
            elapsed = _ms(t0)
        self.assertEqual(r.status_code, 200)
        rows = r.json()["results"]
        self.assertEqual(len(rows), 24)
        # До оптимизации: ~1 query stock на товар (+ availability повтор) ≈ 50+ SQL.
        # После: prefetch stock_items → константный бюджет.
        self.assertLessEqual(
            len(ctx),
            20,
            msg=f"catalog list SQL budget exceeded: {len(ctx)} queries, {elapsed:.1f}ms",
        )
        # available использует активные точки; 5 stores * (5-1) avail per series * 3 series
        sample = next(x for x in rows if x["id"] == str(products[0].pk))
        self.assertGreater(sample["available_quantity_total"], 0)
        print(
            f"[BLOCK6] catalog_list products=24 queries={len(ctx)} time_ms={elapsed:.1f}"
        )

    def test_product_detail_query_budget(self):
        products, _ = self._seed_catalog(2, 9, 3)
        slug = products[0].slug
        with CaptureQueriesContext(connection) as ctx:
            t0 = time.perf_counter()
            r = self.client.get(f"/api/v1/products/products/{slug}/")
            elapsed = _ms(t0)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("stock", body)
        # Одна строка на активный магазин (агрегация серий)
        self.assertEqual(len(body["stock"]), 9)
        self.assertLessEqual(
            len(ctx),
            15,
            msg=f"detail SQL budget exceeded: {len(ctx)} queries, {elapsed:.1f}ms",
        )
        print(
            f"[BLOCK6] product_detail stores=9 series=3 queries={len(ctx)} "
            f"time_ms={elapsed:.1f}"
        )

    def test_single_upsert_query_cost(self):
        p = Product.objects.create(
            title="U",
            slug="perf-upsert-1",
            price=Decimal("1"),
            category=self.category,
            onec_code="PERF-U1",
            is_active=True,
        )
        store = self.stores[TEST_RETAIL_WH_ID]
        with CaptureQueriesContext(connection) as ctx:
            t0 = time.perf_counter()
            with transaction.atomic():
                for i in range(40):
                    apply_onec_stock_upsert(
                        product_id=p.pk,
                        store_id=store.pk,
                        series_id=f"U{i}",
                        series_name="",
                        quantity=2,
                        run_id="block6-single-loop",
                    )
            elapsed = _ms(t0)
        qpr = len(ctx) / 40.0
        print(
            f"[BLOCK6] single_upsert_x40 queries={len(ctx)} q_per_row={qpr:.1f} "
            f"time_ms={elapsed:.1f}"
        )
        # Исторический baseline ~5–8 SQL/row; после batch API отдельный тест.
        self.assertGreater(qpr, 3.0)

    def test_batch_upsert_reduces_sql(self):
        from apps.stores.stock_ops import (
            OnecStockUpsertItem,
            apply_onec_stock_upserts_batch,
        )

        p = Product.objects.create(
            title="B",
            slug="perf-upsert-batch",
            price=Decimal("1"),
            category=self.category,
            onec_code="PERF-UB",
            is_active=True,
        )
        store = self.stores[TEST_RETAIL_WH_ID]
        items = [
            OnecStockUpsertItem(
                product_id=p.pk,
                store_id=store.pk,
                series_id=f"B{i}",
                series_name="",
                quantity=2,
            )
            for i in range(40)
        ]
        with CaptureQueriesContext(connection) as ctx:
            t0 = time.perf_counter()
            with transaction.atomic():
                result = apply_onec_stock_upserts_batch(
                    items, run_id="block6-batch-loop"
                )
            elapsed = _ms(t0)
        self.assertEqual(result["applied"], 40)
        self.assertEqual(Stock.objects.filter(product=p).count(), 40)
        self.assertEqual(
            StockMovement.objects.filter(
                source="onec.importer", reason="onec_stock_upsert"
            ).count(),
            40,
        )
        qpr = len(ctx) / 40.0
        print(
            f"[BLOCK6] batch_upsert_x40 queries={len(ctx)} q_per_row={qpr:.2f} "
            f"time_ms={elapsed:.1f}"
        )
        self.assertLessEqual(len(ctx), 25)
        # Повтор — idempotent skip, мало SQL
        with CaptureQueriesContext(connection) as ctx2:
            with transaction.atomic():
                result2 = apply_onec_stock_upserts_batch(
                    items, run_id="block6-batch-loop"
                )
        self.assertEqual(result2["applied"], 0)
        self.assertEqual(result2["skipped_idempotent"], 40)
        self.assertLessEqual(len(ctx2), 10)

    def test_synthetic_import_scale_and_memory(self):
        """
        Синтетический apply: 1k / 5k stock rows (не 100k в CI — слишком долго на SQLite).
        10k измеряется отдельно если среда позволяет; здесь фиксируем 1k+5k.
        """
        from apps.stores.stock_ops import (
            OnecStockUpsertItem,
            apply_onec_stock_upserts_batch,
        )

        store = self.stores[TEST_RETAIL_WH_ID]
        products = []
        for i in range(100):
            products.append(
                Product.objects.create(
                    title=f"Scale {i}",
                    slug=f"scale-b6-{i}",
                    price=Decimal("10"),
                    category=self.category,
                    onec_code=f"SCALE-{i}",
                    is_active=True,
                )
            )

        def run_rows(n: int, run_id: str):
            items = []
            for i in range(n):
                p = products[i % len(products)]
                items.append(
                    OnecStockUpsertItem(
                        product_id=p.pk,
                        store_id=store.pk,
                        series_id=f"SC-{run_id}-{i}",
                        series_name="",
                        quantity=(i % 5) + 1,
                    )
                )
            gc.collect()
            tracemalloc.start()
            t0 = time.perf_counter()
            with transaction.atomic():
                result = apply_onec_stock_upserts_batch(items, run_id=run_id)
            elapsed = _ms(t0)
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return result, elapsed, peak

        r1, ms1, peak1 = run_rows(1000, "scale-1k")
        self.assertEqual(r1["applied"], 1000)
        r5, ms5, peak5 = run_rows(5000, "scale-5k")
        self.assertEqual(r5["applied"], 5000)
        print(
            f"[BLOCK6] scale_1k applied={r1['applied']} time_ms={ms1:.1f} "
            f"peak_kib={peak1/1024:.1f}"
        )
        print(
            f"[BLOCK6] scale_5k applied={r5['applied']} time_ms={ms5:.1f} "
            f"peak_kib={peak5/1024:.1f}"
        )
        # Sanity: 5k не на порядки хуже линейности по времени от 1k (запас x12)
        self.assertLess(ms5, ms1 * 12 + 5000)

    def test_reserved_preserved_in_batch(self):
        from apps.stores.stock_ops import (
            OnecStockUpsertItem,
            apply_onec_stock_upserts_batch,
        )

        p = Product.objects.create(
            title="R",
            slug="perf-reserved",
            price=Decimal("1"),
            category=self.category,
            onec_code="PERF-R",
            is_active=True,
        )
        store = self.stores[TEST_RETAIL_WH_ID]
        Stock.objects.create(
            product=p,
            store=store,
            onec_series_id="",
            quantity=5,
            reserved_quantity=2,
        )
        with transaction.atomic():
            apply_onec_stock_upserts_batch(
                [
                    OnecStockUpsertItem(
                        product_id=p.pk,
                        store_id=store.pk,
                        series_id="",
                        series_name="",
                        quantity=9,
                    )
                ],
                run_id="block6-reserved",
            )
        row = Stock.objects.get(product=p, store=store, onec_series_id="")
        self.assertEqual(row.quantity, 9)
        self.assertEqual(row.reserved_quantity, 2)

    def test_xml_plan_memory_smoke(self):
        """Разбор синтетического XML ~2k товарных строк + plan (без apply)."""
        from integrations.onec.importer import (
            ImportMode,
            plan_catalog_import_from_xml_strings,
        )

        folders = (
            '<ПапкиНоменклатуры><Папка code="F-PERF" parentCode="" '
            'name="PerfCat"/></ПапкиНоменклатуры>'
        )
        rows = []
        for i in range(2000):
            rows.append(
                f'<Товар code="XML-{i}" parentCode="F-PERF" name="Item {i}" '
                f'price="100" quantity="1" sklad="{TEST_RETAIL_WH_NAME}" '
                f'skladID="{TEST_RETAIL_WH_ID}"/>'
            )
        xml = "<Товары>" + "".join(rows) + "</Товары>"
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        plan = plan_catalog_import_from_xml_strings(
            folders, xml, mode=ImportMode.DRY_RUN
        )
        elapsed = _ms(t0)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertGreaterEqual(len(plan.stocks), 2000)
        print(
            f"[BLOCK6] xml_plan_2k stocks={len(plan.stocks)} time_ms={elapsed:.1f} "
            f"peak_kib={peak/1024:.1f}"
        )
