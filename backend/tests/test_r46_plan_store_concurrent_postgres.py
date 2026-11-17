"""
D.2.3: concurrent claim через независимые PostgreSQL-соединения.

Не имитируется на SQLite. Запуск:

  set RINGOO_TEST_POSTGRES=1
  set DATABASE_URL=postgres://USER:PASS@127.0.0.1:5432/ringoo_test
  set DJANGO_SETTINGS_MODULE=config.settings.test_postgres
  pytest tests/test_r46_plan_store_concurrent_postgres.py -q --no-cov
"""

from __future__ import annotations

import os
import threading
import unittest

import pytest
from django.db import connection
from django.test import TransactionTestCase

from apps.products.sync_models import OneCCatalogImportPlan
from integrations.onec.importer import (
    CatalogImportPlan,
    ImportMode,
    SnapshotPolicy,
)
from integrations.onec.plan_store import (
    PlanStoreError,
    _claim_plan_for_apply,
    apply_saved_plan,
    persist_plan_after_dry_run,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RINGOO_TEST_POSTGRES", "").strip().lower() not in ("1", "true", "yes"),
    reason="Set RINGOO_TEST_POSTGRES=1 + config.settings.test_postgres",
)


def _require_postgres():
    if os.getenv("RINGOO_TEST_POSTGRES", "").strip().lower() not in ("1", "true", "yes"):
        raise unittest.SkipTest(
            "Set RINGOO_TEST_POSTGRES=1 + config.settings.test_postgres"
        )
    if connection.vendor != "postgresql":
        raise unittest.SkipTest(
            "Requires PostgreSQL, got %s" % connection.vendor
        )


def _empty_plan() -> CatalogImportPlan:
    return CatalogImportPlan(
        mode=ImportMode.DRY_RUN.value,
        generated_at="2020-01-01T00:00:00+00:00",
        source_folders_path="folders.xml",
        source_products_path="products.xml",
        run_id="run-conc",
        snapshot_policy=SnapshotPolicy.PRESENT_ONLY.value,
        categories=[],
        products=[],
        stocks=[],
        stocks_to_zero=[],
        warehouses=[],
        issues=[],
        apply_blockers=[],
        summary={},
    )


class ConcurrentClaimPostgresTests(TransactionTestCase):
    def setUp(self):
        _require_postgres()

    def test_two_connections_only_one_claims(self):
        row = persist_plan_after_dry_run(_empty_plan())
        plan_id = str(row.plan_id)
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        lock = threading.Lock()

        def worker():
            connection.close()
            connection.connect()
            try:
                barrier.wait(timeout=10)
                _claim_plan_for_apply(plan_id)
                with lock:
                    outcomes.append("ok")
            except PlanStoreError:
                with lock:
                    outcomes.append("fail")
            finally:
                connection.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)
        self.assertEqual(sorted(outcomes), ["fail", "ok"], outcomes)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_APPLYING)
        self.assertEqual(
            OneCCatalogImportPlan.objects.filter(
                status=OneCCatalogImportPlan.STATUS_APPLYING
            ).count(),
            1,
        )

    def test_reclaim_after_applied_fails(self):
        row = persist_plan_after_dry_run(_empty_plan())
        apply_saved_plan(row.plan_id)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_APPLIED)
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)
