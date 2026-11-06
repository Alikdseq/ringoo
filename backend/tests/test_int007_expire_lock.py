"""INT-007: distributed lock на expire task."""

from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.payments.locks import EXPIRE_LOCK_KEY
from apps.payments.tasks import expire_unpaid_online_orders_task


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "int007",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "int007s",
        },
    },
    PAYMENTS_EXPIRE_LOCK_TTL_SECONDS=60,
)
class ExpireLockTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_second_parallel_skips(self):
        cache.add(EXPIRE_LOCK_KEY, "1", timeout=60)
        result = expire_unpaid_online_orders_task()
        self.assertTrue(result.get("skipped"))
        self.assertEqual(result.get("reason"), "lock_held")

    def test_runs_when_free(self):
        result = expire_unpaid_online_orders_task()
        self.assertNotIn("skipped", result)
        self.assertIn("cancelled", result)
        self.assertFalse(cache.get(EXPIRE_LOCK_KEY))
