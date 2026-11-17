"""Celery: синхронизация каталога 1С."""

from __future__ import annotations

import logging

from django.conf import settings

from config.optional_task import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def run_onec_catalog_sync_task(
    self,
    *,
    dry_run: bool = True,
    user_id: str | None = None,
    plan_id: str | None = None,
    full_snapshot_acknowledged: bool = False,
):
    """
    Асинхронный dry-run/apply каталога.
    APPLY только с plan_id (D.2.1). full_snapshot требует ack (D.2.3).
    """
    from django.contrib.auth import get_user_model

    from integrations.onec.catalog_sync import run_catalog_import

    user = None
    if user_id:
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()

    if not dry_run and not plan_id:
        raise RuntimeError("Celery APPLY требует plan_id")

    return run_catalog_import(
        dry_run=dry_run,
        from_api=True if dry_run else False,
        user=user,
        celery_task_id=getattr(self.request, "id", "") or "",
        plan_id=plan_id if not dry_run else None,
        full_snapshot_acknowledged=bool(full_snapshot_acknowledged),
    )


@shared_task
def scheduled_onec_catalog_sync_task():
    """
    Beat-задача. D.2.1/D.2.3: автоматический APPLY отключён.
    """
    logger.info(
        "scheduled catalog sync skipped: D.2.1 requires plan_id; Beat APPLY disabled"
    )
    return {
        "skipped": True,
        "reason": "d2_plan_id_required",
        "note": "Automatic APPLY via Beat is disabled; use dry-run → plan_id → apply",
    }
