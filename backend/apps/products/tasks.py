"""Celery: синхронизация каталога 1С."""

from __future__ import annotations

import logging

from django.conf import settings

from config.optional_task import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def run_onec_catalog_sync_task(self, *, dry_run: bool = True, user_id: str | None = None):
    """
    Асинхронный dry-run/apply каталога.
    Live HTTP только при ONE_C_API_ENABLED.
    """
    from django.contrib.auth import get_user_model

    from integrations.onec.catalog_sync import run_catalog_import

    user = None
    if user_id:
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()

    return run_catalog_import(
        dry_run=dry_run,
        from_api=True,
        user=user,
        celery_task_id=getattr(self.request, "id", "") or "",
    )


@shared_task
def scheduled_onec_catalog_sync_task():
    """
    Beat-задача. Выполняет apply только если ONE_C_CATALOG_SYNC_ENABLED и API on.
    По умолчанию флаги OFF — no-op.
    """
    if not getattr(settings, "ONE_C_CATALOG_SYNC_ENABLED", False):
        logger.info("scheduled catalog sync skipped: ONE_C_CATALOG_SYNC_ENABLED=false")
        return {"skipped": True, "reason": "flag_off"}
    if not getattr(settings, "ONE_C_API_ENABLED", False):
        logger.info("scheduled catalog sync skipped: ONE_C_API_ENABLED=false")
        return {"skipped": True, "reason": "api_disabled"}
    from integrations.onec.catalog_sync import (
        has_running_apply,
        reap_stale_running_applies,
        run_catalog_import,
    )

    reaped = reap_stale_running_applies()
    if has_running_apply():
        return {"skipped": True, "reason": "already_running", "reaped_stale": reaped}
    return run_catalog_import(dry_run=False, from_api=True, user=None)
