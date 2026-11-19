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
# Весь Beat-цикл dry-run → plan → apply (между Worker/Beat).
AUTO_SYNC_LOCK_CACHE_KEY = "onec:catalog:auto_sync_lock"
# Auto-sync lock допускается только с этим backend (общий Redis).
REQUIRED_AUTO_SYNC_CACHE_BACKEND = "django_redis.cache.RedisCache"


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
            log.duration_ms = int((log.finished_at - log.started_at).total_seconds() * 1000)
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
    logger.warning("onec apply lock: cache backend does not persist; using SyncLog running check only")
    return not _running_apply_in_db()


def _release_apply_lock(run_id: str) -> None:
    current = cache.get(APPLY_LOCK_CACHE_KEY)
    if current == run_id:
        cache.delete(APPLY_LOCK_CACHE_KEY)


def _auto_sync_lock_ttl() -> int:
    return max(60, STALE_RUNNING_MINUTES * 60)


def _is_django_redis_cache_backend() -> bool:
    """True только если default cache — django_redis.cache.RedisCache."""
    conf = (getattr(settings, "CACHES", None) or {}).get("default") or {}
    backend = str(conf.get("BACKEND") or "").strip()
    return backend == REQUIRED_AUTO_SYNC_CACHE_BACKEND


def auto_sync_redis_lock_precheck() -> str | None:
    """
    Skip-reason до обращения к 1С, если распределённый Redis lock недоступен.
    DummyCache / LocMemCache / неизвестный backend → отказ (без process-local fallback).
    """
    if not _is_django_redis_cache_backend():
        conf = (getattr(settings, "CACHES", None) or {}).get("default") or {}
        backend = str(conf.get("BACKEND") or "").strip() or "unset"
        logger.warning(
            "scheduled catalog sync refused: cache backend %s "
            "(required %s)",
            backend,
            REQUIRED_AUTO_SYNC_CACHE_BACKEND,
        )
        return "redis_cache_required"
    return None


def _try_acquire_auto_sync_lock(token: str) -> bool:
    """
    Распределённый lock на весь auto-sync цикл через Redis cache.add (SET NX).
    Без Redis backend — всегда False (см. auto_sync_redis_lock_precheck).
    """
    if not _is_django_redis_cache_backend():
        return False
    ttl = _auto_sync_lock_ttl()
    return bool(cache.add(AUTO_SYNC_LOCK_CACHE_KEY, token, timeout=ttl))


def _release_auto_sync_lock(token: str) -> None:
    """Снимает lock только при совпадении token (не трогает чужой hold)."""
    if not _is_django_redis_cache_backend():
        return
    current = cache.get(AUTO_SYNC_LOCK_CACHE_KEY)
    if current == token:
        cache.delete(AUTO_SYNC_LOCK_CACHE_KEY)


def _parse_auto_sync_thresholds() -> tuple[dict[str, Any] | None, str]:
    """
    Читает пороги без silent fallback для явного 0.
    ratio должен быть в (0, 1]; absolute mins >= 1.
    """
    try:
        # Не использовать `x or default` — иначе 0.0 незаметно станет 0.90.
        raw_min_products = getattr(settings, "ONE_C_CATALOG_AUTO_MIN_UNIQUE_PRODUCTS", 1)
        raw_min_folders = getattr(settings, "ONE_C_CATALOG_AUTO_MIN_FOLDERS", 1)
        raw_product_ratio = getattr(settings, "ONE_C_CATALOG_AUTO_MIN_PRODUCT_RATIO", 0.90)
        raw_category_ratio = getattr(settings, "ONE_C_CATALOG_AUTO_MIN_CATEGORY_RATIO", 0.90)
        min_products = int(raw_min_products)
        min_folders = int(raw_min_folders)
        product_ratio = float(raw_product_ratio)
        category_ratio = float(raw_category_ratio)
    except (TypeError, ValueError):
        return None, "invalid_auto_sync_settings"

    if min_products < 1 or min_folders < 1:
        return None, "invalid_auto_sync_settings"
    if not (0.0 < product_ratio <= 1.0) or not (0.0 < category_ratio <= 1.0):
        return None, "invalid_auto_sync_settings"

    return {
        "min_unique_products": min_products,
        "min_folders": min_folders,
        "product_ratio": product_ratio,
        "category_ratio": category_ratio,
    }, ""


def get_last_applied_catalog_baseline() -> dict[str, Any]:
    """
    Baseline из последнего успешно применённого плана.

    Returns:
      {"ok": True, "baseline": {...}} или
      {"ok": False, "reason": "baseline_missing"|"baseline_invalid", ...}
    """
    from apps.products.sync_models import OneCCatalogImportPlan

    row = (
        OneCCatalogImportPlan.objects.filter(
            status=OneCCatalogImportPlan.STATUS_APPLIED
        )
        .order_by("-applied_at", "-created_at")
        .first()
    )
    if row is None:
        return {"ok": False, "reason": "baseline_missing"}

    payload = row.canonical_payload if isinstance(row.canonical_payload, dict) else None
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "reason": "baseline_invalid",
            "details": {"plan_id": str(row.plan_id), "error": "payload_not_dict"},
        }

    try:
        folders = int(payload["folder_count"])
        unique_products = int(payload["unique_product_count"])
        product_rows = int(payload.get("product_row_count") or 0)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "ok": False,
            "reason": "baseline_invalid",
            "details": {
                "plan_id": str(row.plan_id),
                "error": f"count_parse:{exc.__class__.__name__}",
            },
        }

    if folders <= 0 or unique_products <= 0:
        return {
            "ok": False,
            "reason": "baseline_invalid",
            "details": {
                "plan_id": str(row.plan_id),
                "folder_count": folders,
                "unique_product_count": unique_products,
                "error": "non_positive_counts",
            },
        }

    return {
        "ok": True,
        "baseline": {
            "plan_id": str(row.plan_id),
            "folder_count": folders,
            "unique_product_count": unique_products,
            "product_row_count": product_rows,
            "applied_at": row.applied_at.isoformat() if row.applied_at else None,
        },
    }


def assess_catalog_snapshot_completeness(
    *,
    current_unique_products: int,
    current_folders: int,
    baseline_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Полнота до auto-APPLY: обязательный валидный baseline + ratio.
    Absolute-only без baseline не допускается. Не zero-fill.
    """
    import math

    thresholds, thresh_reason = _parse_auto_sync_thresholds()
    details: dict[str, Any] = {
        "current_unique_products": int(current_unique_products),
        "current_folders": int(current_folders),
        "limitation": (
            "Heuristic vs last applied plan only; 1C API has no TotalCount/"
            "ETag/pagination proof of full export."
        ),
    }
    if thresholds is None:
        details["thresholds_error"] = thresh_reason
        return {
            "ok": False,
            "reason": "invalid_auto_sync_settings",
            "details": details,
        }

    details.update(thresholds)

    if not baseline_result or not baseline_result.get("ok"):
        reason = (
            (baseline_result or {}).get("reason")
            if isinstance(baseline_result, dict)
            else "baseline_missing"
        ) or "baseline_missing"
        details["baseline_result"] = baseline_result
        return {"ok": False, "reason": str(reason), "details": details}

    baseline = baseline_result.get("baseline") or {}
    try:
        base_products = int(baseline["unique_product_count"])
        base_folders = int(baseline["folder_count"])
    except (KeyError, TypeError, ValueError):
        return {
            "ok": False,
            "reason": "baseline_invalid",
            "details": {**details, "baseline": baseline},
        }

    if base_products <= 0 or base_folders <= 0:
        return {
            "ok": False,
            "reason": "baseline_invalid",
            "details": {
                **details,
                "baseline": baseline,
                "error": "non_positive_counts",
            },
        }

    details["baseline"] = baseline
    details["baseline_mode"] = "ratio_vs_applied_plan"

    if int(current_unique_products) < thresholds["min_unique_products"] or int(
        current_folders
    ) < thresholds["min_folders"]:
        return {
            "ok": False,
            "reason": "below_absolute_minimum",
            "details": details,
        }

    required_products = max(
        thresholds["min_unique_products"],
        math.ceil(base_products * thresholds["product_ratio"]),
    )
    required_folders = max(
        thresholds["min_folders"],
        math.ceil(base_folders * thresholds["category_ratio"]),
    )
    details["required_unique_products"] = required_products
    details["required_folders"] = required_folders

    if int(current_unique_products) < required_products or int(current_folders) < required_folders:
        return {
            "ok": False,
            "reason": "incomplete_snapshot",
            "details": details,
        }

    return {"ok": True, "reason": "ok", "details": details}


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
        log.status = OneCCatalogSyncLog.STATUS_SUCCESS if ok else OneCCatalogSyncLog.STATUS_FAILED
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
    snapshot_policy: str | None = None,
    plan_id: str | None = None,
    full_snapshot_acknowledged: bool = False,
) -> dict[str, Any]:
    """
    Dry-run: строит план, сохраняет в PostgreSQL, возвращает plan_id.
    Apply: только по plan_id (не пересобирает XML/API). D.2.1/D.2.3.
    full_snapshot APPLY требует full_snapshot_acknowledged=True.
    """
    from apps.products.sync_models import OneCCatalogSyncLog
    from integrations.onec.importer import (
        ImportMode,
        fetch_and_plan_from_api,
        normalize_snapshot_policy,
        plan_catalog_import,
    )
    from integrations.onec.plan_store import (
        PlanStoreError,
        apply_saved_plan,
        persist_plan_after_dry_run,
    )
    policy = normalize_snapshot_policy(snapshot_policy)

    if not dry_run:
        if not plan_id:
            raise RuntimeError(
                "APPLY требует plan_id сохранённого DRY-RUN плана "
                "(нельзя пересобрать план из XML/API)."
            )
        if from_api and not getattr(settings, "ONE_C_API_ENABLED", False):
            raise RuntimeError("ONE_C_API_ENABLED=false — apply из API запрещён")

    run_id = _new_run_id()
    apply_lock_held = False
    if not dry_run:
        if not _try_acquire_apply_lock(run_id):
            raise RuntimeError("Уже выполняется apply каталога — дождитесь завершения")
        apply_lock_held = True
        if _running_apply_in_db(exclude_run_id=run_id):
            _release_apply_lock(run_id)
            apply_lock_held = False
            raise RuntimeError("Уже выполняется apply каталога — дождитесь завершения")

    source = OneCCatalogSyncLog.SOURCE_API if from_api else OneCCatalogSyncLog.SOURCE_FILE
    if not dry_run:
        source = OneCCatalogSyncLog.SOURCE_FILE  # apply by plan_id; XML/API not re-fetched
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
        from integrations.onec.reporting import (
            build_issue_counts,
            issue_for_log,
            partition_issues,
        )

        apply_result: dict[str, Any] | None = None
        saved_plan_meta: dict[str, Any] = {}

        if dry_run:
            mode = ImportMode.DRY_RUN
            if from_api:
                plan = fetch_and_plan_from_api(mode=mode, snapshot_policy=policy)
            else:
                from pathlib import Path

                plan = plan_catalog_import(
                    Path(folders_path),
                    Path(products_path),
                    mode=mode,
                    snapshot_policy=policy,
                )
            plan.run_id = run_id

            s = plan.summary or {}
            partitioned = partition_issues(plan.issues or [])
            issue_counts = build_issue_counts(partitioned)

            log.records_received = int(plan.product_row_count or 0) + int(plan.folder_count or 0)
            log.categories_created = int(s.get("categories_create") or 0)
            log.categories_updated = int(s.get("categories_update") or 0)
            log.categories_skipped = int(s.get("categories_skip") or 0)
            log.products_created = int(s.get("products_create") or 0)
            log.products_updated = int(s.get("products_update") or 0)
            log.products_skipped = int(s.get("products_skip") or 0)
            log.stocks_upserted = int(s.get("stocks_upsert") or 0)
            log.stocks_skipped = int(s.get("stocks_skip") or 0)
            log.errors_count = int(issue_counts["errors_count"])
            log_msgs: list[Any] = []
            for i in (partitioned["blocker"] + partitioned["error"])[:80]:
                log_msgs.append(issue_for_log(i))
            for i in partitioned["warning"][:40]:
                log_msgs.append(issue_for_log(i))
            for i in partitioned["info"][:5]:
                log_msgs.append(issue_for_log(i))
            log.error_messages = log_msgs

            try:
                saved = persist_plan_after_dry_run(
                    plan, user=user, dry_run_sync_log=log
                )
                saved_plan_meta = {
                    "plan_id": str(saved.plan_id),
                    "plan_checksum": saved.checksum,
                    "plan_expires_at": saved.expires_at.isoformat(),
                    "plan_schema_version": saved.schema_version,
                    "snapshot_policy": saved.snapshot_policy,
                }
            except PlanStoreError as exc:
                raise RuntimeError(f"Не удалось сохранить план: {exc}") from exc

            log.summary = {
                "folder_count": plan.folder_count,
                "product_row_count": plan.product_row_count,
                "unique_product_count": plan.unique_product_count,
                "mode": plan.mode,
                "plan_run_id": plan.run_id,
                "counters_source": "planned",
                "planned_stocks_upsert": int(s.get("stocks_upsert") or 0),
                "planned_stocks_to_zero": int(s.get("stocks_to_zero") or 0),
                "stock_series_rows": int(s.get("stock_series_rows") or 0),
                "warnings_count": issue_counts["warnings_count"],
                "info_count": issue_counts["info_count"],
                "blockers_count": issue_counts["blockers_count"],
                "anomalies_count": 0,
                "stocks_zeroed": 0,
                "stocks_skipped_idempotent": 0,
                **{k: s.get(k) for k in s},
                **issue_counts,
                **saved_plan_meta,
            }
        else:
            # APPLY by plan_id only — no XML/API rebuild.
            apply_result = apply_saved_plan(
                plan_id,
                full_snapshot_acknowledged=bool(full_snapshot_acknowledged),
            )
            saved_plan_meta = {
                "plan_id": str(plan_id),
                "counters_source": "applied",
                "apply_run_id": apply_result.get("run_id") or run_id,
                "full_snapshot_acknowledged": bool(full_snapshot_acknowledged),
            }
            log.products_created = int(apply_result.get("products_created") or 0)
            log.products_updated = int(apply_result.get("products_updated") or 0)
            log.stocks_upserted = int(apply_result.get("stocks_upserted") or 0)
            stock_zeroed = int(apply_result.get("stocks_zeroed") or 0)
            stock_idem = int(apply_result.get("stocks_skipped_idempotent") or 0)
            log.stocks_skipped = stock_idem
            anomalies = int(apply_result.get("reserved_over_quantity_count") or 0)
            log.categories_created = int(apply_result.get("categories") or 0)
            # Snapshot size from applied plan (audit / next auto-sync baseline helper).
            snapshot_counts: dict[str, Any] = {}
            try:
                from apps.products.sync_models import OneCCatalogImportPlan

                plan_row = OneCCatalogImportPlan.objects.filter(pk=plan_id).first()
                payload = (
                    plan_row.canonical_payload
                    if plan_row and isinstance(plan_row.canonical_payload, dict)
                    else {}
                )
                if payload:
                    snapshot_counts = {
                        "folder_count": int(payload.get("folder_count") or 0),
                        "product_row_count": int(payload.get("product_row_count") or 0),
                        "unique_product_count": int(
                            payload.get("unique_product_count") or 0
                        ),
                    }
            except Exception:  # noqa: BLE001
                snapshot_counts = {}
            log.summary = {
                "counters_source": "applied",
                "stocks_zeroed": stock_zeroed,
                "stocks_skipped_idempotent": stock_idem,
                "stocks_upserted_applied": log.stocks_upserted,
                "anomalies_count": anomalies,
                "reserved_over_quantity_count": anomalies,
                **snapshot_counts,
                **saved_plan_meta,
            }

        if log.errors_count > 0:
            log.status = OneCCatalogSyncLog.STATUS_PARTIAL
        else:
            log.status = OneCCatalogSyncLog.STATUS_SUCCESS
    except Exception as exc:  # noqa: BLE001
        logger.exception("onec catalog sync failed run=%s", log.run_id)
        log.status = OneCCatalogSyncLog.STATUS_FAILED
        log.errors_count = max(int(log.errors_count or 0), 1)
        stop_reason = str(exc)[:500]
        log.error_messages = list(log.error_messages or []) + [
            {"type": "stop", "class": "blocker", "message": stop_reason}
        ]
        summary = dict(log.summary or {})
        summary["stop_reason"] = stop_reason
        log.summary = summary
    finally:
        log.finished_at = timezone.now()
        log.duration_ms = int((log.finished_at - started).total_seconds() * 1000)
        log.save()
        if apply_lock_held:
            _release_apply_lock(run_id)

    payload = serialize_sync_log(log)
    summary = log.summary or {}
    if summary.get("plan_id"):
        payload["plan_id"] = summary.get("plan_id")
        payload["plan_checksum"] = summary.get("plan_checksum")
        payload["plan_expires_at"] = summary.get("plan_expires_at")
    return payload


def serialize_sync_log(log) -> dict[str, Any]:
    summary = log.summary or {}
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
        "stocks_zeroed": int(summary.get("stocks_zeroed") or 0),
        "stocks_skipped_idempotent": int(summary.get("stocks_skipped_idempotent") or 0),
        "warnings_count": int(summary.get("warnings_count") or 0),
        "info_count": int(summary.get("info_count") or 0),
        "anomalies_count": int(summary.get("anomalies_count") or 0),
        "errors_count": log.errors_count,
        "stop_reason": summary.get("stop_reason") or None,
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
        OneCCatalogSyncLog.objects.filter(sync_type=OneCCatalogSyncLog.TYPE_CATALOG).order_by("-created_at").first()
    )
    age_hours = None
    stale = True
    if last_ok and last_ok.finished_at:
        age_hours = round((timezone.now() - last_ok.finished_at).total_seconds() / 3600.0, 2)
        threshold = int(getattr(settings, "ONE_C_CATALOG_STALE_HOURS", 24) or 24)
        stale = age_hours > threshold

    return {
        "api_enabled": bool(getattr(settings, "ONE_C_API_ENABLED", False)),
        "catalog_sync_enabled": bool(getattr(settings, "ONE_C_CATALOG_SYNC_ENABLED", False)),
        "partner_sync_on_register": bool(getattr(settings, "ONE_C_SYNC_PARTNER_ON_REGISTER", False)),
        "apply_running": has_running_apply(),
        "last_success": serialize_sync_log(last_ok) if last_ok else None,
        "last_run": serialize_sync_log(last_any) if last_any else None,
        "data_age_hours": age_hours,
        "data_stale": stale if last_ok else True,
        "stale_threshold_hours": int(getattr(settings, "ONE_C_CATALOG_STALE_HOURS", 24) or 24),
    }


def run_scheduled_catalog_auto_sync(*, celery_task_id: str = "") -> dict[str, Any]:
    """
    Beat-оркестратор: lock → dry-run (API, present_only) → completeness → apply.

    Не обходит D.2.1/D.2.3: APPLY только через сохранённый plan_id и
    full_snapshot_acknowledged=False (full_snapshot через Beat не применяется).
    """
    if not getattr(settings, "ONE_C_CATALOG_SYNC_ENABLED", False):
        return {"skipped": True, "reason": "catalog_sync_disabled"}
    if not getattr(settings, "ONE_C_API_ENABLED", False):
        return {"skipped": True, "reason": "api_disabled"}

    # До 1С: только django_redis.RedisCache (без LocMem/Dummy/process-local).
    redis_skip = auto_sync_redis_lock_precheck()
    if redis_skip:
        return {"skipped": True, "reason": redis_skip}

    lock_token = celery_task_id or f"auto-{uuid.uuid4().hex}"
    if not _try_acquire_auto_sync_lock(lock_token):
        return {"skipped": True, "reason": "auto_sync_lock_held"}

    try:
        if has_running_apply():
            return {"skipped": True, "reason": "apply_running"}

        dry = run_catalog_import(
            dry_run=True,
            from_api=True,
            celery_task_id=celery_task_id,
            snapshot_policy="present_only",
        )
        summary = dry.get("summary") or {}
        plan_id = dry.get("plan_id") or summary.get("plan_id")

        if dry.get("status") == "failed" or not plan_id:
            logger.info(
                "scheduled catalog sync skip apply: dry_run_failed status=%s plan_id=%s",
                dry.get("status"),
                plan_id,
            )
            return {"skipped": True, "reason": "dry_run_failed", "dry_run": dry}

        if dry.get("status") != "success" or int(dry.get("errors_count") or 0) > 0:
            logger.info(
                "scheduled catalog sync skip apply: dry_run_not_clean status=%s errors=%s plan_id=%s",
                dry.get("status"),
                dry.get("errors_count"),
                plan_id,
            )
            return {
                "skipped": True,
                "reason": "dry_run_not_clean",
                "plan_id": str(plan_id),
                "dry_run": dry,
            }

        blockers_count = int(summary.get("blockers_count") or 0)
        apply_blockers_meta = summary.get("apply_blockers") or 0
        if isinstance(apply_blockers_meta, list):
            apply_blockers_n = len(apply_blockers_meta)
        else:
            apply_blockers_n = int(apply_blockers_meta or 0)
        if (
            not summary.get("apply_allowed", False)
            or blockers_count > 0
            or apply_blockers_n > 0
        ):
            logger.info(
                "scheduled catalog sync skip apply: apply_blockers plan_id=%s blockers=%s",
                plan_id,
                blockers_count or apply_blockers_n,
            )
            return {
                "skipped": True,
                "reason": "apply_blockers",
                "plan_id": str(plan_id),
                "dry_run": dry,
            }

        snapshot_policy = summary.get("snapshot_policy") or "present_only"
        if snapshot_policy != "present_only":
            logger.info(
                "scheduled catalog sync skip apply: snapshot_policy=%s plan_id=%s",
                snapshot_policy,
                plan_id,
            )
            return {
                "skipped": True,
                "reason": "snapshot_policy_not_present_only",
                "plan_id": str(plan_id),
                "dry_run": dry,
            }

        current_unique = int(summary.get("unique_product_count") or 0)
        current_folders = int(summary.get("folder_count") or 0)
        baseline_result = get_last_applied_catalog_baseline()
        completeness = assess_catalog_snapshot_completeness(
            current_unique_products=current_unique,
            current_folders=current_folders,
            baseline_result=baseline_result,
        )
        if not completeness.get("ok"):
            reason = str(completeness.get("reason") or "incomplete_snapshot")
            logger.warning(
                "scheduled catalog sync skip apply: %s plan_id=%s details=%s",
                reason,
                plan_id,
                completeness.get("details"),
            )
            # План dry-run сохранён для диагностики; APPLY не выполняем.
            return {
                "skipped": True,
                "reason": reason,
                "plan_id": str(plan_id),
                "dry_run": dry,
                "completeness": completeness,
            }

        if has_running_apply():
            return {
                "skipped": True,
                "reason": "apply_running",
                "plan_id": str(plan_id),
                "dry_run": dry,
            }

        applied = run_catalog_import(
            dry_run=False,
            from_api=False,
            plan_id=str(plan_id),
            full_snapshot_acknowledged=False,
            celery_task_id=celery_task_id,
        )
        logger.info(
            "scheduled catalog sync applied plan_id=%s apply_status=%s",
            plan_id,
            applied.get("status"),
        )
        return {
            "skipped": False,
            "plan_id": str(plan_id),
            "dry_run": dry,
            "apply": applied,
            "completeness": completeness,
        }
    finally:
        _release_auto_sync_lock(lock_token)
