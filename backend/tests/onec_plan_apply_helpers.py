"""
Test-only helper: persist CatalogImportPlan and APPLY via plan_store.

Not importable as a production APPLY bypass — gated by Django TESTING.
"""

from __future__ import annotations

from django.conf import settings

from integrations.onec.importer import CatalogImportPlan, SnapshotPolicy, normalize_snapshot_policy
from integrations.onec.plan_store import apply_saved_plan, persist_plan_after_dry_run


def persist_and_apply_for_tests(
    plan: CatalogImportPlan,
    *,
    full_snapshot_acknowledged: bool | None = None,
) -> dict:
    # Refuse outside Django test runner. DEBUG=True shell is not enough.
    if not getattr(settings, "TESTING", False):
        raise RuntimeError(
            "persist_and_apply_for_tests is test-only "
            "(settings.TESTING is required; not available when DEBUG=False "
            "or outside the test environment)"
        )
    row = persist_plan_after_dry_run(plan)
    policy = normalize_snapshot_policy(plan.snapshot_policy)
    if full_snapshot_acknowledged is None:
        # Auto-ack only inside tests when plan itself is full_snapshot.
        full_snapshot_acknowledged = (
            policy == SnapshotPolicy.FULL_SNAPSHOT.value
        )
    return apply_saved_plan(
        row.plan_id,
        full_snapshot_acknowledged=bool(full_snapshot_acknowledged),
    )
