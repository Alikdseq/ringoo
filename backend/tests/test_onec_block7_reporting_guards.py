"""
BLOCK 7 — отчётность SyncLog, ONEC-015/016, защита пустого снимка, dry-run/apply.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase

from apps.products.models import Category, Product
from apps.products.sync_models import OneCCatalogSyncLog
from apps.stores.models import Stock
from integrations.onec.catalog_sync import run_catalog_import
from integrations.onec.importer import (
    ImportMode,
    apply_catalog_import,
    plan_catalog_import_from_xml_strings,
)
from integrations.onec.parser import OneCParseError, parse_catalog_files
from integrations.onec.reporting import classify_issue, partition_issues
from tests.onec_test_utils import (
    TEST_RETAIL_WH_ID,
    TEST_RETAIL_WH_NAME,
    ensure_confirmed_stores,
)


FOLDERS = (
    '<ПапкиНоменклатуры><Папка code="F1" parentCode="" name="Phones"/>'
    "</ПапкиНоменклатуры>"
)


def _xml(*rows: str) -> str:
    return "<Товары>" + "".join(rows) + "</Товары>"


def _row(code, price, qty, *, series="", series_id=""):
    extra = ""
    if series or series_id:
        extra = f' series="{series}" seriesID="{series_id}"'
    return (
        f'<Товар code="{code}" parentCode="F1" name="Phone {code}" '
        f'price="{price}" quantity="{qty}" sklad="{TEST_RETAIL_WH_NAME}" '
        f'skladID="{TEST_RETAIL_WH_ID}"{extra}/>'
    )


class ReportingClassificationTests(TestCase):
    def test_series_present_is_info_not_error(self):
        self.assertEqual(
            classify_issue({"type": "series_present"}),
            "info",
        )
        parts = partition_issues(
            [
                {"type": "series_present", "onec_code": "A"},
                {"type": "unknown_warehouse", "severity": True, "message": "x"},
                {"type": "rejected_price", "onec_code": "B"},
            ]
        )
        self.assertEqual(len(parts["info"]), 1)
        self.assertEqual(len(parts["blocker"]), 1)
        self.assertEqual(len(parts["warning"]), 1)


class EmptySnapshotGuardTests(TestCase):
    def test_parse_catalog_files_empty_products_warns(self):
        with TemporaryDirectory() as tmp:
            folders = Path(tmp) / "folders.xml"
            products = Path(tmp) / "products.xml"
            folders.write_text(
                '<ПапкиНоменклатуры><Папка code="F1" parentCode="" name="X"/>'
                "</ПапкиНоменклатуры>",
                encoding="utf-8",
            )
            products.write_text("<Товары></Товары>", encoding="utf-8")
            parsed = parse_catalog_files(folders, products)
            self.assertTrue(parsed.parse_warnings)
            self.assertFalse(parsed.product_rows)

    def test_empty_products_xml_blocks_plan(self):
        with self.assertRaises(OneCParseError):
            plan_catalog_import_from_xml_strings(
                FOLDERS, "<Товары></Товары>", mode=ImportMode.DRY_RUN
            )


class SyncLogCountersTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.category = Category.objects.create(
            title="Phones", slug="phones-b7", onec_code="F1", is_active=True
        )

    def test_dry_run_does_not_mutate_and_counts_planned(self):
        xml = _xml(
            _row("N-B7-1", "100", 3, series="IMEI", series_id="SER-1"),
            _row("N-B7-1", "100", 2, series="IMEI2", series_id="SER-2"),
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS, xml, mode=ImportMode.DRY_RUN
        )
        self.assertTrue(plan.apply_allowed, plan.apply_blockers)
        self.assertGreaterEqual(plan.summary.get("series_rows", 0), 2)
        self.assertGreaterEqual(plan.summary.get("stock_series_rows", 0), 2)
        self.assertEqual(Product.objects.filter(onec_code="N-B7-1").count(), 0)
        self.assertEqual(Stock.objects.count(), 0)
        parts = partition_issues(plan.issues)
        self.assertGreaterEqual(len(parts["info"]), 2)
        self.assertEqual(len(parts["blocker"]), 0)

    def test_apply_sync_log_uses_applied_not_planned_stocks(self):
        """ONEC-015: повтор apply → stocks_upserted=0, skipped_idempotent>0."""
        xml = _xml(_row("N-B7-A", "100", 5))
        # Первый apply через SyncLog
        with TemporaryDirectory() as tmp:
            folders = Path(tmp) / "f.xml"
            products = Path(tmp) / "p.xml"
            folders.write_text(FOLDERS, encoding="utf-8")
            products.write_text(xml, encoding="utf-8")
            r1 = run_catalog_import(
                dry_run=False,
                from_api=False,
                folders_path=str(folders),
                products_path=str(products),
            )
        self.assertEqual(r1["status"], "success", r1)
        self.assertFalse(r1["dry_run"])
        self.assertGreaterEqual(r1["stocks_upserted"], 1)
        self.assertEqual(r1["summary"].get("counters_source"), "applied")
        planned = int(r1["summary"].get("planned_stocks_upsert") or 0)
        self.assertGreaterEqual(planned, 1)

        # Повтор того же снимка (новый SyncLog run_id → новые ключи → снова applied)
        # Для ONEC-015 нужен тот же plan.run_id. Проверяем apply_catalog_import напрямую:
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS, xml, mode=ImportMode.APPLY
        )
        plan.run_id = "fixed-run-b7-idem"
        a1 = apply_catalog_import(plan)
        self.assertGreaterEqual(a1["stocks_upserted"], 1)
        a2 = apply_catalog_import(plan)
        self.assertEqual(a2["stocks_upserted"], 0)
        self.assertGreaterEqual(a2["stocks_skipped_idempotent"], 1)

        # SyncLog повторного файла: новый run_id → снова upsert (другой ключ) — это OK.
        # Главное: поле stocks_upserted на логе = apply_result, не planned.
        with TemporaryDirectory() as tmp:
            folders = Path(tmp) / "f.xml"
            products = Path(tmp) / "p.xml"
            folders.write_text(FOLDERS, encoding="utf-8")
            products.write_text(xml, encoding="utf-8")
            r2 = run_catalog_import(
                dry_run=False,
                from_api=False,
                folders_path=str(folders),
                products_path=str(products),
            )
        self.assertEqual(r2["summary"].get("counters_source"), "applied")
        self.assertIn("stocks_zeroed", r2)
        self.assertIn("warnings_count", r2)

    def test_series_present_does_not_force_partial(self):
        """ONEC-016: только series_present → success, errors_count=0."""
        xml = _xml(_row("N-B7-S", "50", 1, series="X", series_id="SID-1"))
        with TemporaryDirectory() as tmp:
            folders = Path(tmp) / "f.xml"
            products = Path(tmp) / "p.xml"
            folders.write_text(FOLDERS, encoding="utf-8")
            products.write_text(xml, encoding="utf-8")
            result = run_catalog_import(
                dry_run=True,
                from_api=False,
                folders_path=str(folders),
                products_path=str(products),
            )
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["errors_count"], 0)
        self.assertGreaterEqual(result["info_count"], 1)
        self.assertGreaterEqual(result["summary"].get("series_rows", 0), 1)

    def test_unknown_warehouse_blocks_apply_and_logs_failed(self):
        xml = _xml(
            '<Товар code="N-BAD" parentCode="F1" name="X" price="10" quantity="1" '
            'sklad="Ghost" skladID="00000000-0000-0000-0000-000000000099"/>'
        )
        with TemporaryDirectory() as tmp:
            folders = Path(tmp) / "f.xml"
            products = Path(tmp) / "p.xml"
            folders.write_text(FOLDERS, encoding="utf-8")
            products.write_text(xml, encoding="utf-8")
            result = run_catalog_import(
                dry_run=False,
                from_api=False,
                folders_path=str(folders),
                products_path=str(products),
            )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result.get("stop_reason") or result["errors_count"] >= 1)
        self.assertEqual(Product.objects.filter(onec_code="N-BAD").count(), 0)
        log = OneCCatalogSyncLog.objects.get(run_id=result["run_id"])
        self.assertEqual(log.status, OneCCatalogSyncLog.STATUS_FAILED)

    def test_dry_run_apply_separation(self):
        xml = _xml(_row("N-B7-D", "10", 4))
        with TemporaryDirectory() as tmp:
            folders = Path(tmp) / "f.xml"
            products = Path(tmp) / "p.xml"
            folders.write_text(FOLDERS, encoding="utf-8")
            products.write_text(xml, encoding="utf-8")
            dry = run_catalog_import(
                dry_run=True,
                from_api=False,
                folders_path=str(folders),
                products_path=str(products),
            )
        self.assertTrue(dry["dry_run"])
        self.assertEqual(Product.objects.filter(onec_code="N-B7-D").count(), 0)
        self.assertGreaterEqual(dry["products_created"], 1)  # planned
        self.assertEqual(dry["summary"].get("counters_source"), "planned")
