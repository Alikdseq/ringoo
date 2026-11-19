"""Integration: Beat auto-sync lock, completeness, dry-run→apply, D.2.x guards."""

from __future__ import annotations

from unittest.mock import patch

from django.core.cache import cache, caches
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.products.models import Category, Product
from apps.products.sync_models import OneCCatalogImportPlan
from integrations.onec.client import OneCClientError
from integrations.onec.importer import (
    CatalogImportPlan,
    CategoryAction,
    ImportMode,
    ProductAction,
    SnapshotPolicy,
)
from integrations.onec.plan_store import (
    PlanStoreError,
    _claim_plan_for_apply,
    apply_saved_plan,
    diagnose_stuck_applying_plan,
    persist_plan_after_dry_run,
)
from tests.onec_plan_apply_helpers import persist_and_apply_for_tests
from tests.onec_test_utils import (
    TEST_RETAIL_WH_ID,
    TEST_RETAIL_WH_NAME,
    ensure_confirmed_stores,
)

FOLDERS_XML = (
    '<ПапкиНоменклатуры>'
    '<Папка code="F1" parentCode="" name="Phones"/>'
    '<Папка code="F2" parentCode="" name="Tablets"/>'
    "</ПапкиНоменклатуры>"
)


def _products_xml(*codes: str) -> str:
    rows = []
    for code in codes:
        rows.append(
            f'<Товар code="{code}" parentCode="F1" name="Item {code}" '
            f'price="10.00" quantity="1" sklad="{TEST_RETAIL_WH_NAME}" '
            f'skladID="{TEST_RETAIL_WH_ID}"/>'
        )
    return "<Товары>" + "".join(rows) + "</Товары>"


def _baseline_plan(*, folders: int, unique: int) -> CatalogImportPlan:
    cats = [
        CategoryAction(
            onec_code=f"F{i}",
            name=f"Cat{i}",
            parent_code="",
            action="create",
            site_slug=f"cat-{i}",
        )
        for i in range(1, folders + 1)
    ]
    prods = [
        ProductAction(
            onec_code=f"N{i}",
            name=f"P{i}",
            parent_code="F1",
            price="10.00",
            action="create",
        )
        for i in range(1, unique + 1)
    ]
    return CatalogImportPlan(
        mode=ImportMode.DRY_RUN.value,
        generated_at="2020-01-01T00:00:00+00:00",
        source_folders_path="folders.xml",
        source_products_path="products.xml",
        run_id="baseline-run",
        snapshot_policy=SnapshotPolicy.PRESENT_ONLY.value,
        folder_count=folders,
        product_row_count=unique,
        unique_product_count=unique,
        categories=cats,
        products=prods,
        stocks=[],
        stocks_to_zero=[],
        warehouses=[],
        issues=[],
        apply_blockers=[],
        summary={"apply_allowed": True},
    )


@override_settings(
    ONE_C_CATALOG_SYNC_ENABLED=True,
    ONE_C_API_ENABLED=True,
    ONE_C_CATALOG_AUTO_MIN_PRODUCT_RATIO=0.90,
    ONE_C_CATALOG_AUTO_MIN_CATEGORY_RATIO=0.90,
    ONE_C_CATALOG_AUTO_MIN_UNIQUE_PRODUCTS=1,
    ONE_C_CATALOG_AUTO_MIN_FOLDERS=1,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "auto-sync-integration",
        }
    },
)
class ScheduledCatalogAutoSyncIntegrationTests(TestCase):
    """
    LocMem в settings намеренно: auto-sync должен skip с redis_cache_required
    без патча. Для сценариев после Redis-гейта патчим precheck+lock.
    """

    def setUp(self):
        caches.close_all()
        cache.clear()
        self.stores = ensure_confirmed_stores()
        self._lock_holder: str | None = None

    def _acq(self, token: str) -> bool:
        if self._lock_holder is not None:
            return False
        self._lock_holder = token
        return True

    def _rel(self, token: str) -> None:
        if self._lock_holder == token:
            self._lock_holder = None

    def _redis_ok_patches(self):
        return (
            patch(
                "integrations.onec.catalog_sync.auto_sync_redis_lock_precheck",
                return_value=None,
            ),
            patch(
                "integrations.onec.catalog_sync._try_acquire_auto_sync_lock",
                side_effect=self._acq,
            ),
            patch(
                "integrations.onec.catalog_sync._release_auto_sync_lock",
                side_effect=self._rel,
            ),
        )

    def _seed_applied_baseline(self, *, folders: int = 20, unique: int = 100):
        plan = _baseline_plan(folders=folders, unique=unique)
        row = persist_plan_after_dry_run(plan)
        row.status = OneCCatalogImportPlan.STATUS_APPLIED
        row.applied_at = timezone.now()
        row.execution_token = ""
        row.save(update_fields=["status", "applied_at", "execution_token"])
        return row

    def test_locmem_refuses_before_onec(self):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        with patch("integrations.onec.catalog_sync.run_catalog_import") as mock_import:
            result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "redis_cache_required")
        mock_import.assert_not_called()

    def test_get_last_applied_catalog_baseline(self):
        from integrations.onec.catalog_sync import get_last_applied_catalog_baseline

        missing = get_last_applied_catalog_baseline()
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["reason"], "baseline_missing")

        self._seed_applied_baseline(folders=20, unique=100)
        base = get_last_applied_catalog_baseline()
        self.assertTrue(base["ok"])
        self.assertEqual(base["baseline"]["folder_count"], 20)
        self.assertEqual(base["baseline"]["unique_product_count"], 100)

    def test_baseline_zero_counts_invalid(self):
        from integrations.onec.catalog_sync import get_last_applied_catalog_baseline

        plan = _baseline_plan(folders=1, unique=1)
        plan.folder_count = 0
        plan.unique_product_count = 0
        row = persist_plan_after_dry_run(plan)
        row.status = OneCCatalogImportPlan.STATUS_APPLIED
        row.applied_at = timezone.now()
        row.save(update_fields=["status", "applied_at"])
        # Force zero in stored payload
        payload = dict(row.canonical_payload)
        payload["folder_count"] = 0
        payload["unique_product_count"] = 0
        row.canonical_payload = payload
        row.save(update_fields=["canonical_payload"])

        result = get_last_applied_catalog_baseline()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "baseline_invalid")

    @patch("integrations.onec.client.OneCClient.fetch_products_xml")
    @patch("integrations.onec.client.OneCClient.fetch_folders_xml")
    def test_happy_path_dry_run_apply(self, mock_folders, mock_products):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        self._seed_applied_baseline(folders=2, unique=10)
        codes = tuple(f"N{i}" for i in range(1, 11))
        mock_folders.return_value = FOLDERS_XML
        mock_products.return_value = _products_xml(*codes)

        p1, p2, p3 = self._redis_ok_patches()
        with p1, p2, p3:
            result = run_scheduled_catalog_auto_sync(celery_task_id="int-happy")
        self.assertFalse(result.get("skipped"), result)
        self.assertEqual(result["apply"]["status"], "success")
        self.assertTrue(Product.objects.filter(onec_code="N1").exists())

    @patch("integrations.onec.client.OneCClient.fetch_products_xml")
    @patch("integrations.onec.client.OneCClient.fetch_folders_xml")
    def test_no_baseline_blocks_apply_keeps_plan(self, mock_folders, mock_products):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        mock_folders.return_value = FOLDERS_XML
        mock_products.return_value = _products_xml("N1", "N2")
        p1, p2, p3 = self._redis_ok_patches()
        with p1, p2, p3:
            result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "baseline_missing")
        self.assertEqual(Product.objects.count(), 0)
        self.assertTrue(
            OneCCatalogImportPlan.objects.filter(
                status=OneCCatalogImportPlan.STATUS_READY
            ).exists()
        )

    @patch("integrations.onec.client.OneCClient.fetch_products_xml")
    @patch("integrations.onec.client.OneCClient.fetch_folders_xml")
    def test_sharp_drop_blocks_apply(self, mock_folders, mock_products):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        self._seed_applied_baseline(folders=20, unique=100)
        mock_folders.return_value = FOLDERS_XML
        mock_products.return_value = _products_xml("N1", "N2", "N3")

        p1, p2, p3 = self._redis_ok_patches()
        with p1, p2, p3:
            result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "incomplete_snapshot")
        self.assertEqual(Product.objects.count(), 0)
        plan = OneCCatalogImportPlan.objects.exclude(
            status=OneCCatalogImportPlan.STATUS_APPLIED
        ).latest("created_at")
        self.assertEqual(plan.status, OneCCatalogImportPlan.STATUS_READY)

    @patch("integrations.onec.client.OneCClient.fetch_folders_xml")
    def test_onec_timeout_skips(self, mock_folders):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        mock_folders.side_effect = OneCClientError("1C timeout", status_code=504)
        p1, p2, p3 = self._redis_ok_patches()
        with p1, p2, p3:
            result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "dry_run_failed")

    def test_parallel_auto_sync_lock(self):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        self._lock_holder = "holder-1"
        p1, p2, p3 = self._redis_ok_patches()
        with p1, p2, p3:
            with patch(
                "integrations.onec.catalog_sync.run_catalog_import"
            ) as mock_import:
                result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "auto_sync_lock_held")
        mock_import.assert_not_called()

    def test_manual_import_unaffected_by_auto_sync_redis_gate(self):
        """Ручной dry-run→apply не требует auto-sync Redis gate."""
        cat = Category.objects.create(title="Man", slug="man-c", onec_code="F1")
        plan = CatalogImportPlan(
            mode=ImportMode.DRY_RUN.value,
            generated_at="2020-01-01T00:00:00+00:00",
            source_folders_path="f.xml",
            source_products_path="p.xml",
            run_id="manual-run",
            snapshot_policy=SnapshotPolicy.PRESENT_ONLY.value,
            folder_count=1,
            product_row_count=1,
            unique_product_count=1,
            categories=[
                CategoryAction(
                    onec_code="F1",
                    name="Phones",
                    parent_code="",
                    action="update",
                    site_id=str(cat.id),
                    site_slug="phones",
                )
            ],
            products=[
                ProductAction(
                    onec_code="N-MAN",
                    name="Manual",
                    parent_code="F1",
                    price="3.00",
                    action="create",
                )
            ],
            stocks=[],
            stocks_to_zero=[],
            warehouses=[],
            issues=[],
            apply_blockers=[],
            summary={},
        )
        persist_and_apply_for_tests(plan)
        self.assertTrue(Product.objects.filter(onec_code="N-MAN").exists())

    def test_apply_error_rolls_back_and_rejects_plan(self):
        cat = Category.objects.create(title="C", slug="rb-c", onec_code="F1")
        plan = CatalogImportPlan(
            mode=ImportMode.DRY_RUN.value,
            generated_at="2020-01-01T00:00:00+00:00",
            source_folders_path="f.xml",
            source_products_path="p.xml",
            run_id="rb-run",
            snapshot_policy=SnapshotPolicy.PRESENT_ONLY.value,
            folder_count=1,
            product_row_count=1,
            unique_product_count=1,
            categories=[
                CategoryAction(
                    onec_code="F1",
                    name="Phones",
                    parent_code="",
                    action="update",
                    site_id=str(cat.id),
                    site_slug="phones",
                )
            ],
            products=[
                ProductAction(
                    onec_code="N-RB",
                    name="Boom",
                    parent_code="F1",
                    price="1.00",
                    action="create",
                )
            ],
            stocks=[],
            stocks_to_zero=[],
            warehouses=[],
            issues=[],
            apply_blockers=[],
            summary={},
        )
        row = persist_plan_after_dry_run(plan)
        with patch(
            "integrations.onec.importer.Product.objects.create",
            side_effect=RuntimeError("boom mid-apply"),
        ):
            with self.assertRaises(RuntimeError):
                apply_saved_plan(row.plan_id, full_snapshot_acknowledged=False)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_REJECTED)
        self.assertFalse(Product.objects.filter(onec_code="N-RB").exists())

    def test_plan_id_cannot_apply_twice(self):
        cat = Category.objects.create(title="C2", slug="twice-c", onec_code="F1")
        plan = CatalogImportPlan(
            mode=ImportMode.DRY_RUN.value,
            generated_at="2020-01-01T00:00:00+00:00",
            source_folders_path="f.xml",
            source_products_path="p.xml",
            run_id="twice-run",
            snapshot_policy=SnapshotPolicy.PRESENT_ONLY.value,
            folder_count=1,
            product_row_count=1,
            unique_product_count=1,
            categories=[
                CategoryAction(
                    onec_code="F1",
                    name="Phones",
                    parent_code="",
                    action="update",
                    site_id=str(cat.id),
                    site_slug="phones",
                )
            ],
            products=[
                ProductAction(
                    onec_code="N-TW",
                    name="Twice",
                    parent_code="F1",
                    price="2.00",
                    action="create",
                )
            ],
            stocks=[],
            stocks_to_zero=[],
            warehouses=[],
            issues=[],
            apply_blockers=[],
            summary={},
        )
        persist_and_apply_for_tests(plan)
        row = OneCCatalogImportPlan.objects.latest("created_at")
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_APPLIED)
        with self.assertRaises(PlanStoreError):
            apply_saved_plan(row.plan_id, full_snapshot_acknowledged=False)

    def test_stuck_applying_blocks_reclaim(self):
        plan = _baseline_plan(folders=1, unique=1)
        row = persist_plan_after_dry_run(plan)
        _claim_plan_for_apply(row.plan_id, full_snapshot_acknowledged=False)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_APPLYING)
        info = diagnose_stuck_applying_plan(row.plan_id)
        self.assertEqual(info["status"], OneCCatalogImportPlan.STATUS_APPLYING)
        with self.assertRaises(PlanStoreError):
            apply_saved_plan(row.plan_id, full_snapshot_acknowledged=False)
