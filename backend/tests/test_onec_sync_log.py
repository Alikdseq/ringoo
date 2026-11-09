"""SyncLog + dry-run из fixtures без live 1С."""

from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.products.sync_models import OneCCatalogSyncLog
from integrations.onec.catalog_sync import run_catalog_import

User = get_user_model()
FIXTURES = Path(__file__).resolve().parents[1] / "integrations" / "onec" / "fixtures"


@override_settings(ADMIN_OTP_ENABLED=False, ONE_C_API_ENABLED=False)
class OneCSyncLogTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="79004445566", password="pass", is_staff=True, is_superuser=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_dry_run_from_fixtures_writes_log(self):
        folders = FIXTURES / "sample_folders.xml"
        products = FIXTURES / "sample_products.xml"
        if not folders.is_file():
            self.skipTest("fixtures missing")
        result = run_catalog_import(
            dry_run=True,
            from_api=False,
            folders_path=str(folders),
            products_path=str(products),
            user=self.admin,
        )
        self.assertIn(result["status"], ("success", "partial_success"))
        self.assertTrue(result["dry_run"])
        self.assertTrue(OneCCatalogSyncLog.objects.filter(run_id=result["run_id"]).exists())
        # dry-run не создаёт товары
        from apps.products.models import Product

        self.assertEqual(Product.objects.filter(onec_code__isnull=False).count(), 0)

    def test_status_endpoint(self):
        resp = self.client.get("/api/v1/admin/onec/sync/status/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("api_enabled", resp.data)
        self.assertFalse(resp.data["api_enabled"])

    def test_apply_blocked_when_api_disabled(self):
        resp = self.client.post(
            "/api/v1/admin/onec/sync/apply/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data.get("code"), "onec_api_disabled")

    def test_reap_stale_running_marks_failed(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.products.sync_models import OneCCatalogSyncLog
        from integrations.onec.catalog_sync import (
            STALE_RUNNING_MINUTES,
            reap_stale_running_applies,
        )

        old = timezone.now() - timedelta(minutes=STALE_RUNNING_MINUTES + 5)
        log = OneCCatalogSyncLog.objects.create(
            run_id="stale-run-1",
            sync_type=OneCCatalogSyncLog.TYPE_CATALOG,
            source=OneCCatalogSyncLog.SOURCE_FILE,
            status=OneCCatalogSyncLog.STATUS_RUNNING,
            dry_run=False,
            started_at=old,
        )
        n = reap_stale_running_applies()
        self.assertEqual(n, 1)
        log.refresh_from_db()
        self.assertEqual(log.status, OneCCatalogSyncLog.STATUS_FAILED)

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "onec-apply-lock-test",
            }
        }
    )
    def test_apply_lock_rejects_second_holder(self):
        from django.core.cache import cache, caches

        from integrations.onec.catalog_sync import (
            APPLY_LOCK_CACHE_KEY,
            _release_apply_lock,
            _try_acquire_apply_lock,
        )

        caches.close_all()
        cache.clear()
        self.assertTrue(_try_acquire_apply_lock("run-a"))
        self.assertFalse(_try_acquire_apply_lock("run-b"))
        _release_apply_lock("run-a")
        self.assertTrue(_try_acquire_apply_lock("run-b"))
        _release_apply_lock("run-b")
        self.assertIsNone(cache.get(APPLY_LOCK_CACHE_KEY))
