"""RELEASE 46.1 Stage D.2.1/D.2.3: plan storage, claim token, APPLY by plan_id."""

from __future__ import annotations

import copy
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.products.sync_models import OneCCatalogImportPlan
from integrations.onec.importer import (
    CatalogImportPlan,
    CategoryAction,
    ImportMode,
    ProductAction,
    SnapshotPolicy,
    StockAction,
    apply_catalog_import,
    _apply_catalog_import_plan,
)
from integrations.onec.plan_security import catalog_plan_checksum
from integrations.onec.plan_store import (
    STORAGE_VERSION,
    PlanStoreError,
    _ExecutionGate,
    _LIVE_GATE_IDS,
    _claim_plan_for_apply,
    _consume_execution_token,
    apply_saved_plan,
    deserialize_catalog_plan,
    diagnose_stuck_applying_plan,
    manually_resolve_stuck_plan,
    persist_plan_after_dry_run,
    serialize_catalog_plan,
)
from tests.onec_plan_apply_helpers import persist_and_apply_for_tests


def _sample_plan(**overrides) -> CatalogImportPlan:
    plan = CatalogImportPlan(
        mode=ImportMode.DRY_RUN.value,
        generated_at="2020-01-01T00:00:00+00:00",
        source_folders_path="folders.xml",
        source_products_path="products.xml",
        run_id="run-d2",
        snapshot_policy=SnapshotPolicy.PRESENT_ONLY.value,
        categories=[
            CategoryAction(
                onec_code="F1",
                name="Phones",
                parent_code="",
                action="create",
                site_slug="phones",
            )
        ],
        products=[
            ProductAction(
                onec_code="N1",
                name="Phone",
                parent_code="F1",
                price="10.50",
                action="create",
            )
        ],
        stocks=[
            StockAction(
                onec_code="N1",
                sklad="Retail",
                sklad_id="wh-1",
                quantity="3",
                quantity_status="positive",
                action="upsert",
            )
        ],
        stocks_to_zero=[],
        warehouses=[{"sklad": "Retail", "sklad_id": "wh-1"}],
        issues=[],
        apply_blockers=[],
        summary={},
    )
    for k, v in overrides.items():
        setattr(plan, k, v)
    return plan


def _empty_plan(**overrides) -> CatalogImportPlan:
    return _sample_plan(
        categories=[],
        products=[],
        stocks=[],
        warehouses=[],
        **overrides,
    )


def _full_snapshot_plan(**overrides) -> CatalogImportPlan:
    return _sample_plan(
        snapshot_policy=SnapshotPolicy.FULL_SNAPSHOT.value, **overrides
    )


class PlanSerializeRoundTripTests(TestCase):
    def test_round_trip_checksum_stable(self):
        plan = _sample_plan()
        payload = serialize_catalog_plan(plan)
        restored = deserialize_catalog_plan(payload)
        self.assertEqual(catalog_plan_checksum(plan), catalog_plan_checksum(restored))

    def test_none_vs_empty_string(self):
        a = _sample_plan(
            products=[
                ProductAction(
                    onec_code="N1", name="P", parent_code="F1", price=None, action="skip"
                )
            ]
        )
        b = _sample_plan(
            products=[
                ProductAction(
                    onec_code="N1", name="P", parent_code="F1", price="", action="skip"
                )
            ]
        )
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_empty_lists(self):
        plan = _sample_plan(
            categories=[], products=[], stocks=[], warehouses=[], issues=[]
        )
        restored = deserialize_catalog_plan(serialize_catalog_plan(plan))
        self.assertEqual(restored.categories, [])

    def test_decimal_in_issue_prices_round_trip(self):
        plan = _sample_plan(
            issues=[
                {
                    "type": "product_price_variants",
                    "prices": [Decimal("10.50"), "11.00"],
                    "onec_code": "N1",
                }
            ]
        )
        restored = deserialize_catalog_plan(serialize_catalog_plan(plan))
        self.assertEqual(catalog_plan_checksum(plan), catalog_plan_checksum(restored))

    def test_bad_payload_rejected(self):
        with self.assertRaises(PlanStoreError):
            deserialize_catalog_plan({"storage_version": STORAGE_VERSION})

    def test_unknown_storage_version_rejected(self):
        payload = serialize_catalog_plan(_sample_plan())
        payload["storage_version"] = 999
        with self.assertRaises(PlanStoreError):
            deserialize_catalog_plan(payload)

    def test_unknown_schema_version_rejected(self):
        payload = serialize_catalog_plan(_sample_plan())
        payload["schema_version"] = 999
        with self.assertRaises(PlanStoreError):
            deserialize_catalog_plan(payload)


class PlanPersistAndIntegrityTests(TestCase):
    def test_persist_ready_and_round_trip(self):
        plan = _sample_plan()
        row = persist_plan_after_dry_run(plan)
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_READY)
        restored = deserialize_catalog_plan(row.canonical_payload)
        self.assertEqual(catalog_plan_checksum(restored), row.checksum)

    def test_tamper_payload_detected(self):
        row = persist_plan_after_dry_run(_sample_plan())
        payload = copy.deepcopy(row.canonical_payload)
        payload["products"][0]["price"] = "99.99"
        row.canonical_payload = payload
        row.save(update_fields=["canonical_payload"])
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_REJECTED)

    def test_tamper_checksum_field_detected(self):
        row = persist_plan_after_dry_run(_sample_plan())
        row.checksum = "0" * 64
        row.save(update_fields=["checksum"])
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_REJECTED)

    def test_tamper_stocks_to_zero_detected(self):
        row = persist_plan_after_dry_run(_sample_plan())
        payload = copy.deepcopy(row.canonical_payload)
        payload["stocks_to_zero"] = [
            {
                "onec_code": "N2",
                "sklad": "Retail",
                "sklad_id": "wh-1",
                "quantity": "0",
                "quantity_status": "zeroed",
                "action": "zero",
                "notes": "",
                "series": "",
                "series_id": "",
                "site_product_id": "p",
                "site_store_id": "s",
            }
        ]
        row.canonical_payload = payload
        row.save(update_fields=["canonical_payload"])
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)

    def test_tamper_blockers_detected(self):
        row = persist_plan_after_dry_run(_sample_plan())
        payload = copy.deepcopy(row.canonical_payload)
        payload["apply_blockers"] = [
            {"type": "x", "message": "blocked", "onec_code": "", "sklad_id": ""}
        ]
        row.canonical_payload = payload
        row.save(update_fields=["canonical_payload"])
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)


class PlanStatusTtlTests(TestCase):
    def test_expired_refuses_apply(self):
        row = persist_plan_after_dry_run(_sample_plan())
        row.expires_at = timezone.now() - timedelta(seconds=1)
        row.save(update_fields=["expires_at"])
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_EXPIRED)

    def test_applied_cannot_reclaim(self):
        row = persist_plan_after_dry_run(_empty_plan())
        apply_saved_plan(row.plan_id)
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)

    def test_applying_cannot_reclaim(self):
        row = persist_plan_after_dry_run(_empty_plan())
        _claim_plan_for_apply(row.plan_id)
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)

    def test_rejected_cannot_apply(self):
        row = persist_plan_after_dry_run(_sample_plan())
        row.status = OneCCatalogImportPlan.STATUS_REJECTED
        row.save(update_fields=["status"])
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(row.plan_id)


class CapabilitySecurityTests(TestCase):
    def test_forged_execution_gate_rejected(self):
        from apps.products.models import Category

        before = Category.objects.count()
        plan = _empty_plan(mode=ImportMode.APPLY.value)
        forged = _ExecutionGate(plan_id=persist_plan_after_dry_run(plan).plan_id)
        with self.assertRaises(PlanStoreError):
            _apply_catalog_import_plan(
                plan, gate=forged, expected_plan_id=forged.plan_id
            )
        self.assertEqual(Category.objects.count(), before)

    def test_executor_without_claim_rejected(self):
        from apps.products.models import Category

        before = Category.objects.count()
        plan = _empty_plan(mode=ImportMode.APPLY.value)
        with self.assertRaises(PlanStoreError):
            _apply_catalog_import_plan(
                plan,
                gate=object(),
                expected_plan_id=persist_plan_after_dry_run(plan).plan_id,
            )
        self.assertEqual(Category.objects.count(), before)

    def test_gate_other_plan_id_rejected(self):
        row_a = persist_plan_after_dry_run(_empty_plan())
        row_b = persist_plan_after_dry_run(_empty_plan())
        plan, claimed, token = _claim_plan_for_apply(row_a.plan_id)
        gate = _consume_execution_token(claimed.plan_id, token)
        with self.assertRaises(PlanStoreError):
            _apply_catalog_import_plan(
                plan, gate=gate, expected_plan_id=row_b.plan_id
            )

    def test_token_reuse_rejected(self):
        row = persist_plan_after_dry_run(_empty_plan())
        _plan, claimed, token = _claim_plan_for_apply(row.plan_id)
        _consume_execution_token(claimed.plan_id, token)
        with self.assertRaises(PlanStoreError):
            _consume_execution_token(claimed.plan_id, token)

    def test_gate_reuse_rejected(self):
        row = persist_plan_after_dry_run(_empty_plan())
        plan, claimed, token = _claim_plan_for_apply(row.plan_id)
        gate = _consume_execution_token(claimed.plan_id, token)
        _apply_catalog_import_plan(
            plan, gate=gate, expected_plan_id=claimed.plan_id
        )
        with self.assertRaises(PlanStoreError):
            _apply_catalog_import_plan(
                plan, gate=gate, expected_plan_id=claimed.plan_id
            )

    def test_bare_apply_catalog_import_rejected(self):
        with self.assertRaises(PermissionError):
            apply_catalog_import(_empty_plan(mode=ImportMode.APPLY.value))

    def test_helper_blocked_outside_testing(self):
        self.assertTrue(settings.TESTING)
        with override_settings(TESTING=False):
            with self.assertRaises(RuntimeError):
                persist_and_apply_for_tests(_empty_plan())

    def test_reject_before_write_on_bad_gate(self):
        from apps.products.models import Category, Product

        plan = _sample_plan(mode=ImportMode.APPLY.value)
        row = persist_plan_after_dry_run(plan)
        claimed_plan, claimed, token = _claim_plan_for_apply(row.plan_id)
        gate = _consume_execution_token(claimed.plan_id, token)
        cats_before = Category.objects.count()
        prods_before = Product.objects.count()
        # Drop live registration to simulate forged/stale gate mid-path.
        _LIVE_GATE_IDS.discard(id(gate))
        with self.assertRaises(PlanStoreError):
            _apply_catalog_import_plan(
                claimed_plan, gate=gate, expected_plan_id=claimed.plan_id
            )
        self.assertEqual(Category.objects.count(), cats_before)
        self.assertEqual(Product.objects.count(), prods_before)

    def test_rollback_catalog_on_apply_error(self):
        from apps.products.models import Category

        plan = _sample_plan(mode=ImportMode.APPLY.value)
        row = persist_plan_after_dry_run(plan)
        cats_before = Category.objects.count()
        with patch(
            "integrations.onec.importer.Category.objects.create",
            side_effect=RuntimeError("boom mid-apply"),
        ):
            with self.assertRaises(RuntimeError):
                apply_saved_plan(row.plan_id)
        self.assertEqual(Category.objects.count(), cats_before)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_REJECTED)


class FullSnapshotAckTests(TestCase):
    def test_full_snapshot_claim_requires_ack(self):
        row = persist_plan_after_dry_run(_full_snapshot_plan())
        with self.assertRaises(PlanStoreError) as ctx:
            _claim_plan_for_apply(row.plan_id, full_snapshot_acknowledged=False)
        self.assertIn("full_snapshot_acknowledged", str(ctx.exception))
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_READY)

    def test_full_snapshot_claim_with_ack(self):
        row = persist_plan_after_dry_run(_full_snapshot_plan())
        plan, claimed, token = _claim_plan_for_apply(
            row.plan_id, full_snapshot_acknowledged=True
        )
        self.assertEqual(claimed.status, OneCCatalogImportPlan.STATUS_APPLYING)
        self.assertTrue(token)

    def test_present_only_without_fs_ack(self):
        row = persist_plan_after_dry_run(_sample_plan())
        _claim_plan_for_apply(row.plan_id, full_snapshot_acknowledged=False)
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_APPLYING)

    def test_celery_and_run_require_ack_for_full_snapshot(self):
        from integrations.onec.catalog_sync import run_catalog_import

        row = persist_plan_after_dry_run(_full_snapshot_plan())
        result = run_catalog_import(
            dry_run=False,
            from_api=False,
            plan_id=str(row.plan_id),
            full_snapshot_acknowledged=False,
        )
        self.assertEqual(result["status"], "failed")
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_READY)


class StuckApplyingTests(TestCase):
    def test_diagnose_stuck_applying(self):
        row = persist_plan_after_dry_run(_sample_plan())
        _claim_plan_for_apply(row.plan_id)
        info = diagnose_stuck_applying_plan(row.plan_id)
        self.assertEqual(info["status"], "applying")
        self.assertTrue(info["applying_at"])
        self.assertTrue(info["execution_token_present"])

    def test_stuck_not_auto_ready(self):
        row = persist_plan_after_dry_run(_sample_plan())
        plan, claimed, token = _claim_plan_for_apply(row.plan_id)
        _consume_execution_token(claimed.plan_id, token)
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, "applying")
        self.assertFalse(claimed.execution_token)
        # TTL expire path does not revive to ready
        claimed.expires_at = timezone.now() - timedelta(hours=1)
        claimed.save(update_fields=["expires_at"])
        with self.assertRaises(PlanStoreError):
            _claim_plan_for_apply(claimed.plan_id)
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, "applying")

    def test_manual_resolve_rejected_with_audit(self):
        row = persist_plan_after_dry_run(_sample_plan())
        _claim_plan_for_apply(row.plan_id)
        out = manually_resolve_stuck_plan(
            row.plan_id, resolution="rejected", note="ops: uncertain outcome"
        )
        self.assertEqual(out["status"], "rejected")
        self.assertIn("ops:", out["resolution_note"])
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_REJECTED)

    def test_manual_resolve_cannot_go_ready(self):
        row = persist_plan_after_dry_run(_sample_plan())
        _claim_plan_for_apply(row.plan_id)
        with self.assertRaises(PlanStoreError):
            manually_resolve_stuck_plan(
                row.plan_id, resolution="ready", note="bad"
            )


class BypassPathTests(TestCase):
    def test_beat_skips_apply(self):
        from apps.products.tasks import scheduled_onec_catalog_sync_task

        result = scheduled_onec_catalog_sync_task()
        self.assertEqual(result.get("reason"), "d2_plan_id_required")

    def test_celery_apply_requires_plan_id(self):
        from apps.products.tasks import run_onec_catalog_sync_task

        with self.assertRaises(RuntimeError):
            run_onec_catalog_sync_task.run(dry_run=False, plan_id=None)

    def test_run_catalog_import_apply_requires_plan_id(self):
        from integrations.onec.catalog_sync import run_catalog_import

        with self.assertRaises(RuntimeError):
            run_catalog_import(dry_run=False, from_api=False)

    def test_mutating_memory_plan_after_persist_does_not_change_stored(self):
        plan = _sample_plan()
        row = persist_plan_after_dry_run(plan)
        checksum = row.checksum
        plan.products[0].price = "999.00"
        row.refresh_from_db()
        self.assertEqual(row.checksum, checksum)


class AdminCeleryCliAckTests(TestCase):
    def test_celery_full_snapshot_without_ack_fails(self):
        from apps.products.tasks import run_onec_catalog_sync_task

        row = persist_plan_after_dry_run(_full_snapshot_plan())
        result = run_onec_catalog_sync_task.run(
            dry_run=False,
            plan_id=str(row.plan_id),
            full_snapshot_acknowledged=False,
        )
        self.assertEqual(result["status"], "failed")
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_READY)

    def test_celery_full_snapshot_with_ack_applies(self):
        from apps.products.tasks import run_onec_catalog_sync_task

        row = persist_plan_after_dry_run(
            _full_snapshot_plan(
                categories=[], products=[], stocks=[], warehouses=[]
            )
        )
        result = run_onec_catalog_sync_task.run(
            dry_run=False,
            plan_id=str(row.plan_id),
            full_snapshot_acknowledged=True,
        )
        self.assertIn(result["status"], ("success", "partial_success"))
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_APPLIED)

    def test_cli_full_snapshot_apply_without_ack_fails(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        import io

        row = persist_plan_after_dry_run(
            _full_snapshot_plan(
                categories=[], products=[], stocks=[], warehouses=[]
            )
        )
        err = io.StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command(
                "import_onec_catalog",
                "--apply",
                "--plan-id",
                str(row.plan_id),
                "--i-understand-apply",
                stdout=err,
                stderr=err,
            )
        self.assertIn("failed", str(ctx.exception).lower())
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_READY)

    def test_cli_present_only_apply_without_fs_ack_ok(self):
        from django.core.management import call_command
        import io
        import tempfile
        from pathlib import Path

        row = persist_plan_after_dry_run(_empty_plan())
        with tempfile.TemporaryDirectory() as tmp:
            report = str(Path(tmp) / "r.json")
            out = io.StringIO()
            call_command(
                "import_onec_catalog",
                "--apply",
                "--plan-id",
                str(row.plan_id),
                "--i-understand-apply",
                "--report",
                report,
                stdout=out,
            )
        row.refresh_from_db()
        self.assertEqual(row.status, OneCCatalogImportPlan.STATUS_APPLIED)

    @override_settings(ONE_C_API_ENABLED=True, ADMIN_OTP_ENABLED=False)
    def test_admin_confirm_alone_not_full_snapshot_ack(self):
        from unittest.mock import MagicMock, patch

        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        User = get_user_model()
        admin = User.objects.create_user(
            phone="79001112233", password="pass", is_staff=True, is_superuser=True
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        row = persist_plan_after_dry_run(_full_snapshot_plan())
        mocked = MagicMock()
        mocked.id = "task-fs-ack"
        with patch(
            "apps.products.tasks.run_onec_catalog_sync_task.delay",
            return_value=mocked,
        ) as delay:
            resp = client.post(
                "/api/v1/admin/onec/sync/apply/",
                {"confirm": True, "plan_id": str(row.plan_id)},
                format="json",
            )
        self.assertEqual(resp.status_code, 202, resp.content)
        self.assertFalse(resp.data.get("full_snapshot_acknowledged"))
        kwargs = delay.call_args.kwargs
        self.assertFalse(kwargs.get("full_snapshot_acknowledged"))
        self.assertEqual(kwargs.get("plan_id"), str(row.plan_id))
