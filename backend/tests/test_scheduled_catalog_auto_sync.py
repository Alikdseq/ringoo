"""Beat auto-sync: Redis-only lock, mandatory baseline, ratio gates."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.core.cache import cache, caches
from django.test import SimpleTestCase, TestCase, override_settings


def _clean_dry_run(**overrides):
    payload = {
        "status": "success",
        "errors_count": 0,
        "plan_id": "11111111-1111-1111-1111-111111111111",
        "summary": {
            "plan_id": "11111111-1111-1111-1111-111111111111",
            "apply_allowed": True,
            "blockers_count": 0,
            "apply_blockers": 0,
            "snapshot_policy": "present_only",
            "unique_product_count": 100,
            "folder_count": 20,
        },
    }
    payload.update(overrides)
    if "summary" in overrides:
        summary = {
            "plan_id": "11111111-1111-1111-1111-111111111111",
            "apply_allowed": True,
            "blockers_count": 0,
            "apply_blockers": 0,
            "snapshot_policy": "present_only",
            "unique_product_count": 100,
            "folder_count": 20,
        }
        summary.update(overrides["summary"])
        payload["summary"] = summary
    return payload


def _valid_baseline_result(**overrides):
    baseline = {
        "plan_id": "22222222-2222-2222-2222-222222222222",
        "unique_product_count": 100,
        "folder_count": 20,
        "product_row_count": 100,
        "applied_at": "2020-01-01T00:00:00+00:00",
    }
    baseline.update(overrides)
    return {"ok": True, "baseline": baseline}


class CompletenessGateUnitTests(SimpleTestCase):
    @override_settings(
        ONE_C_CATALOG_AUTO_MIN_PRODUCT_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_CATEGORY_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_UNIQUE_PRODUCTS=1,
        ONE_C_CATALOG_AUTO_MIN_FOLDERS=1,
    )
    def test_ok_with_valid_baseline(self):
        from integrations.onec.catalog_sync import assess_catalog_snapshot_completeness

        result = assess_catalog_snapshot_completeness(
            current_unique_products=95,
            current_folders=19,
            baseline_result=_valid_baseline_result(),
        )
        self.assertTrue(result["ok"])

    @override_settings(
        ONE_C_CATALOG_AUTO_MIN_PRODUCT_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_CATEGORY_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_UNIQUE_PRODUCTS=1,
        ONE_C_CATALOG_AUTO_MIN_FOLDERS=1,
    )
    def test_sharp_drop_products(self):
        from integrations.onec.catalog_sync import assess_catalog_snapshot_completeness

        result = assess_catalog_snapshot_completeness(
            current_unique_products=50,
            current_folders=20,
            baseline_result=_valid_baseline_result(),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "incomplete_snapshot")

    @override_settings(
        ONE_C_CATALOG_AUTO_MIN_PRODUCT_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_CATEGORY_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_UNIQUE_PRODUCTS=1,
        ONE_C_CATALOG_AUTO_MIN_FOLDERS=1,
    )
    def test_missing_baseline_blocks(self):
        from integrations.onec.catalog_sync import assess_catalog_snapshot_completeness

        result = assess_catalog_snapshot_completeness(
            current_unique_products=100,
            current_folders=20,
            baseline_result={"ok": False, "reason": "baseline_missing"},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "baseline_missing")

    @override_settings(
        ONE_C_CATALOG_AUTO_MIN_PRODUCT_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_CATEGORY_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_UNIQUE_PRODUCTS=1,
        ONE_C_CATALOG_AUTO_MIN_FOLDERS=1,
    )
    def test_invalid_zero_baseline_blocks(self):
        from integrations.onec.catalog_sync import assess_catalog_snapshot_completeness

        result = assess_catalog_snapshot_completeness(
            current_unique_products=10,
            current_folders=2,
            baseline_result={
                "ok": True,
                "baseline": {"unique_product_count": 0, "folder_count": 20},
            },
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "baseline_invalid")

    @override_settings(
        ONE_C_CATALOG_AUTO_MIN_PRODUCT_RATIO=0.0,
        ONE_C_CATALOG_AUTO_MIN_CATEGORY_RATIO=0.90,
        ONE_C_CATALOG_AUTO_MIN_UNIQUE_PRODUCTS=1,
        ONE_C_CATALOG_AUTO_MIN_FOLDERS=1,
    )
    def test_explicit_zero_ratio_is_invalid_not_silent_default(self):
        from integrations.onec.catalog_sync import assess_catalog_snapshot_completeness

        result = assess_catalog_snapshot_completeness(
            current_unique_products=100,
            current_folders=20,
            baseline_result=_valid_baseline_result(),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "invalid_auto_sync_settings")


@override_settings(ONE_C_CATALOG_SYNC_ENABLED=True, ONE_C_API_ENABLED=True)
class ScheduledCatalogAutoSyncTests(SimpleTestCase):
    @override_settings(ONE_C_CATALOG_SYNC_ENABLED=False, ONE_C_API_ENABLED=True)
    @patch("integrations.onec.catalog_sync.run_catalog_import")
    def test_skip_when_catalog_sync_disabled(self, mock_import):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "catalog_sync_disabled")
        mock_import.assert_not_called()

    @override_settings(ONE_C_CATALOG_SYNC_ENABLED=True, ONE_C_API_ENABLED=False)
    @patch("integrations.onec.catalog_sync.run_catalog_import")
    def test_skip_when_api_disabled(self, mock_import):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "api_disabled")
        mock_import.assert_not_called()

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        }
    )
    @patch("integrations.onec.catalog_sync.run_catalog_import")
    def test_skip_dummy_cache_before_onec(self, mock_import):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "redis_cache_required")
        mock_import.assert_not_called()

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "auto-sync-refuse-locmem",
            }
        }
    )
    @patch("integrations.onec.catalog_sync.run_catalog_import")
    def test_skip_locmem_cache_before_onec(self, mock_import):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "redis_cache_required")
        mock_import.assert_not_called()

    @patch("integrations.onec.catalog_sync.auto_sync_redis_lock_precheck", return_value=None)
    @patch("integrations.onec.catalog_sync._try_acquire_auto_sync_lock", return_value=False)
    @patch("integrations.onec.catalog_sync.run_catalog_import")
    def test_skip_when_auto_sync_lock_held(self, mock_import, _mock_lock, _pre):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "auto_sync_lock_held")
        mock_import.assert_not_called()

    @patch("integrations.onec.catalog_sync.auto_sync_redis_lock_precheck", return_value=None)
    @patch("integrations.onec.catalog_sync._try_acquire_auto_sync_lock", return_value=True)
    @patch("integrations.onec.catalog_sync._release_auto_sync_lock")
    @patch("integrations.onec.catalog_sync.has_running_apply", return_value=True)
    @patch("integrations.onec.catalog_sync.run_catalog_import")
    def test_skip_when_apply_running(self, mock_import, _h, _rel, _acq, _pre):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "apply_running")
        mock_import.assert_not_called()
        _rel.assert_called_once()

    @patch(
        "integrations.onec.catalog_sync.get_last_applied_catalog_baseline",
        return_value={"ok": False, "reason": "baseline_missing"},
    )
    @patch("integrations.onec.catalog_sync.auto_sync_redis_lock_precheck", return_value=None)
    @patch("integrations.onec.catalog_sync._try_acquire_auto_sync_lock", return_value=True)
    @patch("integrations.onec.catalog_sync._release_auto_sync_lock")
    @patch("integrations.onec.catalog_sync.has_running_apply", return_value=False)
    @patch("integrations.onec.catalog_sync.run_catalog_import")
    def test_skip_apply_when_no_baseline(self, mock_import, _h, _rel, _acq, _pre, _base):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        mock_import.return_value = _clean_dry_run()
        result = run_scheduled_catalog_auto_sync()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "baseline_missing")
        self.assertEqual(mock_import.call_count, 1)
        self.assertTrue(mock_import.call_args.kwargs.get("dry_run"))

    @patch(
        "integrations.onec.catalog_sync.get_last_applied_catalog_baseline",
        return_value=_valid_baseline_result(),
    )
    @patch("integrations.onec.catalog_sync.auto_sync_redis_lock_precheck", return_value=None)
    @patch("integrations.onec.catalog_sync._try_acquire_auto_sync_lock", return_value=True)
    @patch("integrations.onec.catalog_sync._release_auto_sync_lock")
    @patch("integrations.onec.catalog_sync.has_running_apply", return_value=False)
    @patch("integrations.onec.catalog_sync.run_catalog_import")
    def test_happy_path_dry_run_then_apply(self, mock_import, _h, _rel, _acq, _pre, _base):
        from integrations.onec.catalog_sync import run_scheduled_catalog_auto_sync

        dry = _clean_dry_run()
        applied = {"status": "success", "errors_count": 0, "plan_id": dry["plan_id"]}
        mock_import.side_effect = [dry, applied]

        result = run_scheduled_catalog_auto_sync(celery_task_id="beat-1")
        self.assertFalse(result["skipped"])
        self.assertEqual(mock_import.call_count, 2)
        apply_call = mock_import.call_args_list[1]
        self.assertFalse(apply_call.kwargs["dry_run"])
        self.assertFalse(apply_call.kwargs["full_snapshot_acknowledged"])
        _rel.assert_called_once()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://127.0.0.1:6379/15",
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "ringoo_autosync_lock_test",
        }
    }
)
class AutoSyncRedisLockSemanticsTests(TestCase):
    """
    Проверка token/TTL-семантики lock при заявленном Redis backend.
    cache.add мокается как два независимых клиента к одному store.
    """

    def setUp(self):
        self.store: dict = {}

    def _install_shared_store_cache(self):
        """Два независимых mock-client'а с общим dict (имитация Redis SET NX)."""

        def make_client():
            client = MagicMock()

            def add(key, value, timeout=None):
                if key in self.store:
                    return False
                self.store[key] = value
                return True

            def get(key, default=None):
                return self.store.get(key, default)

            def delete(key):
                self.store.pop(key, None)

            client.add.side_effect = add
            client.get.side_effect = get
            client.delete.side_effect = delete
            return client

        return make_client(), make_client()

    @patch("integrations.onec.catalog_sync._is_django_redis_cache_backend", return_value=True)
    def test_two_clients_only_one_acquires(self, _redis_ok):
        from integrations.onec.catalog_sync import (
            AUTO_SYNC_LOCK_CACHE_KEY,
            _try_acquire_auto_sync_lock,
        )

        client_a, client_b = self._install_shared_store_cache()
        with patch("integrations.onec.catalog_sync.cache", client_a):
            self.assertTrue(_try_acquire_auto_sync_lock("token-a"))
        with patch("integrations.onec.catalog_sync.cache", client_b):
            self.assertFalse(_try_acquire_auto_sync_lock("token-b"))
        self.assertEqual(self.store.get(AUTO_SYNC_LOCK_CACHE_KEY), "token-a")

    @patch("integrations.onec.catalog_sync._is_django_redis_cache_backend", return_value=True)
    def test_release_old_token_does_not_delete_new_lock(self, _redis_ok):
        from integrations.onec.catalog_sync import (
            AUTO_SYNC_LOCK_CACHE_KEY,
            _release_auto_sync_lock,
            _try_acquire_auto_sync_lock,
        )

        client_a, client_b = self._install_shared_store_cache()
        with patch("integrations.onec.catalog_sync.cache", client_a):
            self.assertTrue(_try_acquire_auto_sync_lock("token-old"))
            # TTL expiry simulation: clear and let B acquire
            self.store.clear()
        with patch("integrations.onec.catalog_sync.cache", client_b):
            self.assertTrue(_try_acquire_auto_sync_lock("token-new"))
        with patch("integrations.onec.catalog_sync.cache", client_a):
            _release_auto_sync_lock("token-old")
        self.assertEqual(self.store.get(AUTO_SYNC_LOCK_CACHE_KEY), "token-new")
        with patch("integrations.onec.catalog_sync.cache", client_b):
            _release_auto_sync_lock("token-new")
        self.assertNotIn(AUTO_SYNC_LOCK_CACHE_KEY, self.store)

    def test_try_acquire_false_when_backend_not_redis(self):
        from integrations.onec.catalog_sync import _try_acquire_auto_sync_lock

        with patch(
            "integrations.onec.catalog_sync._is_django_redis_cache_backend",
            return_value=False,
        ):
            self.assertFalse(_try_acquire_auto_sync_lock("x"))
