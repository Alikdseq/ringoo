"""
Безопасный запуск импорта каталога с журналом OneCCatalogSyncLog.

Не выполняет live HTTP, если ONE_C_API_ENABLED=false.
Параллельный apply блокируется cache.add (Redis в prod) + статусом SyncLog.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Глобальный ключ «последний успешный apply» храним как успешный SyncLog.
STALE_RUNNING_MINUTES = 120
APPLY_LOCK_CACHE_KEY = "onec:catalog:apply_lock"


def _new_run_id() -> str:
    return f"onec-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def last_successful_apply():
    from apps.products.sync_models import OneCCatalogSyncLog

    return (
        OneCCatalogSyncLog.objects.filter(
            sync_type=OneCCatalogSyncLog.TYPE_CATALOG,
            dry_run=False,
            status=OneCCatalogSyncLog.STATUS_SUCCESS,
        )
        .order_by("-finished_at")
        .first()
    )


def reap_stale_running_applies() -> int:
    """
    Пометить зависшие STATUS_RUNNING (старше STALE_RUNNING_MINUTES) как failed.
    Не трогает свежие running и не сбрасывает без порога возраста.
    """
    from apps.products.sync_models import OneCCatalogSyncLog

    cutoff = timezone.now() - timedelta(minutes=STALE_RUNNING_MINUTES)
    stale = OneCCatalogSyncLog.objects.filter(
        sync_type=OneCCatalogSyncLog.TYPE_CATALOG,
        status=OneCCatalogSyncLog.STATUS_RUNNING,
        started_at__lt=cutoff,
    )
    n = 0
    for log in stale.iterator():
        log.status = OneCCatalogSyncLog.STATUS_FAILED
        log.finished_at = timezone.now()
        if log.started_at:
            log.duration_ms = int(
                (log.finished_at - log.started_at).total_seconds() * 1000
            )
        msgs = list(log.error_messages or [])
        msgs.append(
            {
                "type": "stale_running",
                "message": (
                    f"Запись stuck running >{STALE_RUNNING_MINUTES} мин — "
                    "помечена failed (возможна незавершённая apply; сверьте каталог)."
                )[:400],
            }
        )
        log.error_messages = msgs
        log.errors_count = max(int(log.errors_count or 0), 1)
        log.save(
            update_fields=[
                "status",
                "finished_at",
                "duration_ms",
                "error_messages",
                "errors_count",
            ]
        )
        n += 1
        logger.warning("reaped stale onec SyncLog run_id=%s", log.run_id)
    return n


def has_running_apply() -> bool:
    reap_stale_running_applies()
    if cache.get(APPLY_LOCK_CACHE_KEY):
        return True
    cutoff = timezone.now() - timedelta(minutes=STALE_RUNNING_MINUTES)
    from apps.products.sync_models import OneCCatalogSyncLog

    return OneCCatalogSyncLog.objects.filter(
        sync_type=OneCCatalogSyncLog.TYPE_CATALOG,
        dry_run=False,
        status=OneCCatalogSyncLog.STATUS_RUNNING,
        started_at__gte=cutoff,
    ).exists()


def _cache_persists_locks() -> bool:
    """DummyCache.add всегда True и ничего не хранит — для тестов/misconfig."""
    try:
        probe = f"{APPLY_LOCK_CACHE_KEY}:probe:{uuid.uuid4().hex}"
        if not cache.add(probe, "1", timeout=5):
            return True  # ключ занят — backend реально хранит
        ok = cache.get(probe) == "1"
        cache.delete(probe)
        return ok
    except Exception:  # noqa: BLE001
        return False


def _running_apply_in_db(*, exclude_run_id: str = "") -> bool:
    from apps.products.sync_models import OneCCatalogSyncLog

    cutoff = timezone.now() - timedelta(minutes=STALE_RUNNING_MINUTES)
    qs = OneCCatalogSyncLog.objects.filter(
        sync_type=OneCCatalogSyncLog.TYPE_CATALOG,
        dry_run=False,
        status=OneCCatalogSyncLog.STATUS_RUNNING,
        started_at__gte=cutoff,
    )
    if exclude_run_id:
        qs = qs.exclude(run_id=exclude_run_id)
    return qs.exists()


def _try_acquire_apply_lock(run_id: str) -> bool:
    """
    Атомарный lock через cache.add (в prod — Redis).
    Если cache не персистит (DummyCache) — fallback на отсутствие SyncLog running.
    """
    ttl = max(60, STALE_RUNNING_MINUTES * 60)
    if _cache_persists_locks():
        return bool(cache.add(APPLY_LOCK_CACHE_KEY, run_id, timeout=ttl))
    logger.warning(
        "onec apply lock: cache backend does not persist; using SyncLog running check only"
    )
    return not _running_apply_in_db()


def _release_apply_lock(run_id: str) -> None:
    current = cache.get(APPLY_LOCK_CACHE_KEY)
    if current == run_id:
        cache.delete(APPLY_LOCK_CACHE_KEY)


def probe_connection(*, user=None) -> dict[str, Any]:
    """
    Лёгкая проверка: создаёт SyncLog TYPE_PROBE.
    Не пишет каталог. Live GET только при ONE_C_API_ENABLED.
    """
    from apps.products.sync_models import OneCCatalogSyncLog
    from integrations.onec.client import OneCClient, OneCClientError

    log = OneCCatalogSyncLog.objects.create(
        run_id=_new_run_id(),
        sync_type=OneCCatalogSyncLog.TYPE_PROBE,
        source=OneCCatalogSyncLog.SOURCE_API,
        status=OneCCatalogSyncLog.STATUS_RUNNING,
        dry_run=True,
        started_at=timezone.now(),
        triggered_by=user if getattr(user, "is_authenticated", False) else None,
    )
    started = timezone.now()
    try:
        if not getattr(settings, "ONE_C_API_ENABLED", False):
            raise OneCClientError("ONE_C_API_ENABLED=false — проверка сети пропущена")
        client = OneCClient()
        # HEAD/GET folders — минимальный smoke без записи
        xml = client.fetch_folders_xml()
        ok = bool(xml and len(xml) > 20)
        log.status = (
            OneCCatalogSyncLog.STATUS_SUCCESS if ok else OneCCatalogSyncLog.STATUS_FAILED
        )
        log.summary = {"folders_xml_bytes": len(xml or "")}
        if not ok:
            log.error_messages = ["Пустой ответ CatalogFolders/folders"]
            log.errors_count = 1
    except Exception as exc:  # noqa: BLE001
        log.status = OneCCatalogSyncLog.STATUS_FAILED
        log.errors_count = 1
        # Без секретов
        log.error_messages = [str(exc)[:500]]
        logger.warning("onec probe failed: %s", exc)
    finally:
        log.finished_at = timezone.now()
        log.duration_ms = int((log.finished_at - started).total_seconds() * 1000)
        log.save()
    return serialize_sync_log(log)


def run_catalog_import(
    *,
    dry_run: bool = True,
    from_api: bool = True,
    user=None,
    folders_path: str = "",
    products_path: str = "",
    celery_task_id: str = "",
) -> dict[str, Any]:
    """
    Dry-run или apply поверх существующего importer.
    Apply требует ONE_C_API_ENABLED при from_api=True и отсутствие parallel apply.
    """
    from apps.products.sync_models import OneCCatalogSyncLog
    from integrations.onec.importer import (
        ImportMode,
        apply_catalog_import,
        fetch_and_plan_from_api,
        plan_catalog_import,
    )

    if not dry_run and from_api and not getattr(settings, "ONE_C_API_ENABLED", False):
        raise RuntimeError("ONE_C_API_ENABLED=false — apply из API запрещён")

    run_id = _new_run_id()
    apply_lock_held = False
    if not dry_run:
        # Атомарный cache.add — иначе два Celery worker оба проходят .exists() и оба apply.
        if not _try_acquire_apply_lock(run_id):
            raise RuntimeError("Уже выполняется apply каталога — дождитесь завершения")
        apply_lock_held = True
        # Зависшие SyncLog STATUS_RUNNING без активного lock всё ещё блокируют.
        if _running_apply_in_db(exclude_run_id=run_id):
            _release_apply_lock(run_id)
            apply_lock_held = False
            raise RuntimeError("Уже выполняется apply каталога — дождитесь завершения")

    source = (
        OneCCatalogSyncLog.SOURCE_API
        if from_api
        else OneCCatalogSyncLog.SOURCE_FILE
    )
    log = OneCCatalogSyncLog.objects.create(
        run_id=run_id,
        sync_type=OneCCatalogSyncLog.TYPE_CATALOG,
        source=source,
        status=OneCCatalogSyncLog.STATUS_RUNNING,
        dry_run=dry_run,
        started_at=timezone.now(),
        triggered_by=user if getattr(user, "is_authenticated", False) else None,
        celery_task_id=celery_task_id or "",
    )
    started = timezone.now()
    try:
        mode = ImportMode.DRY_RUN if dry_run else ImportMode.APPLY
        if from_api:
            plan = fetch_and_plan_from_api(mode=mode)
        else:
            from pathlib import Path

            plan = plan_catalog_import(
                Path(folders_path), Path(products_path), mode=mode
            )

        s = plan.summary or {}
        log.records_received = int(plan.product_row_count or 0) + int(
            plan.folder_count or 0
        )
        log.categories_created = int(s.get("categories_create") or 0)
        log.categories_updated = int(s.get("categories_update") or 0)
        log.categories_skipped = int(s.get("categories_skip") or 0)
        log.products_created = int(s.get("products_create") or 0)
        log.products_updated = int(s.get("products_update") or 0)
        log.products_skipped = int(s.get("products_skip") or 0)
        log.stocks_upserted = int(s.get("stocks_upsert") or 0)
        log.stocks_skipped = int(s.get("stocks_skip") or 0)

        issues = plan.issues or []
        log.errors_count = len(issues)
        log.error_messages = [
            {
                "type": i.get("type"),
                "onec_code": i.get("onec_code") or "",
                "field": i.get("field") or "",
                "value": str(i.get("value") if i.get("value") is not None else "")[:64],
                "reason": i.get("reason") or "",
                "message": (i.get("message") or i.get("notes") or str(i))[:400],
            }
            for i in issues[:100]
            if isinstance(i, dict)
        ]
        log.summary = {
            "folder_count": plan.folder_count,
            "product_row_count": plan.product_row_count,
            "unique_product_count": plan.unique_product_count,
            "mode": plan.mode,
            **{k: s.get(k) for k in s},
        }

        if not dry_run:
            with transaction.atomic():
                apply_catalog_import(plan)

        if log.errors_count and (
            log.products_created or log.products_updated or log.categories_created
        ):
            log.status = OneCCatalogSyncLog.STATUS_PARTIAL
        elif log.errors_count and not (
            log.products_created or log.products_updated or log.categories_updated
        ):
            # dry-run с issues всё ещё success плана; failed только при исключениях
            log.status = (
                OneCCatalogSyncLog.STATUS_PARTIAL
                if issues
                else OneCCatalogSyncLog.STATUS_SUCCESS
            )
        else:
            log.status = OneCCatalogSyncLog.STATUS_SUCCESS
    except Exception as exc:  # noqa: BLE001
        logger.exception("onec catalog sync failed run=%s", log.run_id)
        log.status = OneCCatalogSyncLog.STATUS_FAILED
        log.errors_count = max(log.errors_count, 1)
        log.error_messages = list(log.error_messages or []) + [str(exc)[:500]]
    finally:
        log.finished_at = timezone.now()
        log.duration_ms = int((log.finished_at - started).total_seconds() * 1000)
        log.save()
        if apply_lock_held:
            _release_apply_lock(run_id)

    return serialize_sync_log(log)


def serialize_sync_log(log) -> dict[str, Any]:
    return {
        "id": str(log.pk),
        "run_id": log.run_id,
        "sync_type": log.sync_type,
        "source": log.source,
        "status": log.status,
        "dry_run": log.dry_run,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
        "duration_ms": log.duration_ms,
        "records_received": log.records_received,
        "categories_created": log.categories_created,
        "categories_updated": log.categories_updated,
        "categories_skipped": log.categories_skipped,
        "products_created": log.products_created,
        "products_updated": log.products_updated,
        "products_skipped": log.products_skipped,
        "stocks_upserted": log.stocks_upserted,
        "stocks_skipped": log.stocks_skipped,
        "errors_count": log.errors_count,
        "error_messages": log.error_messages,
        "summary": log.summary,
        "celery_task_id": log.celery_task_id,
        "triggered_by_id": str(log.triggered_by_id) if log.triggered_by_id else None,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def sync_status_payload() -> dict[str, Any]:
    from apps.products.sync_models import OneCCatalogSyncLog

    last_ok = last_successful_apply()
    last_any = (
        OneCCatalogSyncLog.objects.filter(sync_type=OneCCatalogSyncLog.TYPE_CATALOG)
        .order_by("-created_at")
        .first()
    )
    age_hours = None
    stale = True
    if last_ok and last_ok.finished_at:
        age_hours = round(
            (timezone.now() - last_ok.finished_at).total_seconds() / 3600.0, 2
        )
        threshold = int(
            getattr(settings, "ONE_C_CATALOG_STALE_HOURS", 24) or 24
        )
        stale = age_hours > threshold

    return {
        "api_enabled": bool(getattr(settings, "ONE_C_API_ENABLED", False)),
        "catalog_sync_enabled": bool(
            getattr(settings, "ONE_C_CATALOG_SYNC_ENABLED", False)
        ),
        "partner_sync_on_register": bool(
            getattr(settings, "ONE_C_SYNC_PARTNER_ON_REGISTER", False)
        ),
        "apply_running": has_running_apply(),
        "last_success": serialize_sync_log(last_ok) if last_ok else None,
        "last_run": serialize_sync_log(last_any) if last_any else None,
        "data_age_hours": age_hours,
        "data_stale": stale if last_ok else True,
        "stale_threshold_hours": int(
            getattr(settings, "ONE_C_CATALOG_STALE_HOURS", 24) or 24
        ),
    }
