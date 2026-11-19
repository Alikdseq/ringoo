"""
Dry-run классификатора витринной таксономии (S1.2.5).

READ-ONLY: только SELECT через Adapter + Classifier в памяти.
Не создаёт ClassificationRun / Event / Assignment / Queue.
Не вызывает save/update/delete/bulk_*.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.products.models import Product
from apps.storefront_taxonomy.adapters.orm import (
    ClassificationInputBundle,
    load_category_map,
    load_overrides_for_products,
    product_to_features,
    rule_to_input,
)
from apps.storefront_taxonomy.engine.classifier import (
    ClassificationBatchResult,
    ClassificationItemResult,
    ItemOutcome,
    classify_bundle,
)
from apps.storefront_taxonomy.engine.resolution_types import ResolutionStatus
from apps.storefront_taxonomy.models import ClassificationRule, StorefrontCategory
from apps.storefront_taxonomy.services.report import REPORT_VERSION

ASSIGNED_STATUSES = frozenset(
    {
        ResolutionStatus.MATCH.value,
        ResolutionStatus.OVERRIDE.value,
        ResolutionStatus.OVERRIDE_FALLBACK.value,
    }
)

PROBLEMATIC_STATUSES = frozenset(
    {
        ResolutionStatus.CONFLICT.value,
        ResolutionStatus.UNMATCHED.value,
        ResolutionStatus.NEEDS_REVIEW.value,
        "error",
    }
)

STATUS_COUNTER_KEYS = (
    "match",
    "override",
    "override_fallback",
    "conflict",
    "unmatched",
    "needs_review",
    "error",
)


class DryRunError(Exception):
    """Критическая ошибка Dry-run (структура / фатальный сбой)."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _path_join(titles: tuple[str, ...]) -> str:
    return " / ".join(titles) if titles else ""


def _matched_info_dicts(item: ClassificationItemResult) -> list[dict[str, Any]]:
    if item.resolution is None:
        return []
    return [
        {
            "rule_id": m.rule_id,
            "code": m.code,
            "priority": m.priority,
            "category_id": m.category_id,
        }
        for m in item.resolution.best_priority_matches
    ]


def _rule_error_dicts(item: ClassificationItemResult) -> list[dict[str, Any]]:
    if item.resolution is None:
        return []
    return [
        {
            "rule_id": e.rule_id,
            "code": e.code,
            "condition_type": e.condition_type,
            "error_type": e.error_type,
            "message": e.message,
        }
        for e in item.resolution.rule_errors
    ]


def _skipped_dicts(item: ClassificationItemResult) -> list[dict[str, Any]]:
    if item.resolution is None:
        return []
    return [
        {
            "rule_id": s.rule_id,
            "code": s.code,
            "reason": s.reason,
        }
        for s in item.resolution.skipped_rules
    ]


def _classification_status(item: ClassificationItemResult) -> str:
    if item.outcome == ItemOutcome.ERROR or item.resolution is None:
        return "error"
    return item.resolution.status.value


def _load_products(*, limit: int | None) -> list[Product]:
    qs = Product.objects.select_related("category").order_by("id")
    if limit is not None:
        if limit < 0:
            raise DryRunError("--limit не может быть отрицательным.")
        qs = qs[:limit]
    return list(qs)


def _build_bundle(
    products: list[Product],
) -> tuple[ClassificationInputBundle, dict[str, dict[str, Any]], list[ClassificationRule]]:
    """
    Bulk-сборка bundle + метаданные товаров + ORM-правила для статистики.

    Запросы (фиксированное число, без N+1):
    - Category.all (через load_category_map)
    - Product уже загружены вызывающим
    - ClassificationRule.select_related
    - Overrides.filter(product_id__in=...)
    """
    categories_by_id = load_category_map()

    features_by_product_id: dict[str, Any] = {}
    product_meta: dict[str, dict[str, Any]] = {}
    product_ids: list[UUID] = []

    for product in products:
        pid = str(product.id)
        product_ids.append(product.id)
        features = product_to_features(product, categories_by_id=categories_by_id)
        features_by_product_id[pid] = features

        src = product.category
        product_meta[pid] = {
            "product_id": pid,
            "title": product.title,
            "sku": product.sku,
            "onec_code": product.onec_code,
            "is_active": bool(product.is_active),
            "source_category_id": str(src.id) if src is not None else None,
            "source_category_title": src.title if src is not None else None,
            "source_category_slug": src.slug if src is not None else None,
            "source_category_path": _path_join(features.category_title_path),
        }

    rules_orm = list(
        ClassificationRule.objects.select_related("storefront_category").order_by(
            "priority", "code", "id"
        )
    )
    rules = tuple(rule_to_input(rule) for rule in rules_orm)
    overrides = load_overrides_for_products(product_ids)

    bundle = ClassificationInputBundle(
        features_by_product_id=features_by_product_id,
        rules=rules,
        overrides_by_product_id=overrides,
    )
    return bundle, product_meta, rules_orm


def _aggregate_report(
    *,
    batch: ClassificationBatchResult,
    product_meta: dict[str, dict[str, Any]],
    rules_orm: list[ClassificationRule],
    storefront_categories: list[StorefrontCategory],
    diagnostics: list[str],
    limit: int | None,
    started_monotonic: float,
) -> dict[str, Any]:
    sf_by_id = {str(c.id): c for c in storefront_categories}
    total_products = len(product_meta)
    active_products = sum(1 for m in product_meta.values() if m["is_active"])
    inactive_products = total_products - active_products

    status_counts = {k: 0 for k in STATUS_COUNTER_KEYS}

    # per storefront category accumulators
    cat_stats: dict[str, dict[str, int]] = {
        str(c.id): {
            "total_products": 0,
            "active_products": 0,
            "inactive_products": 0,
            "match_count": 0,
            "override_count": 0,
            "override_fallback_count": 0,
        }
        for c in storefront_categories
    }

    # per rule accumulators
    rule_stats: dict[str, dict[str, int]] = {
        str(r.id): {
            "matched_count": 0,
            "conflict_count": 0,
            "error_count": 0,
            "skipped_count": 0,
        }
        for r in rules_orm
    }

    items: list[dict[str, Any]] = []
    by_id = batch.by_product_id()

    # Детерминированный порядок товаров
    for pid in sorted(product_meta.keys()):
        meta = product_meta[pid]
        item = by_id.get(pid)
        if item is None:
            diagnostics.append(
                f"Товар {pid} отсутствует в результате Classifier — помечен как error."
            )
            status = "error"
            status_counts["error"] += 1
            row = {
                **meta,
                "classification_status": status,
                "storefront_category_id": None,
                "storefront_category_title": None,
                "storefront_category_slug": None,
                "source": None,
                "fingerprint": None,
                "matched_rules": [],
                "conflicting_categories": [],
                "rule_errors": [],
                "skipped_rules": [],
                "explanation": None,
                "technical_error_type": "MissingClassificationResult",
                "technical_error_message": "Результат Classifier отсутствует для товара.",
            }
            items.append(row)
            continue

        status = _classification_status(item)
        status_counts[status] = status_counts.get(status, 0) + 1

        resolution = item.resolution
        sf_id = resolution.category_id if resolution is not None else None
        sf = sf_by_id.get(sf_id) if sf_id else None

        if status in ASSIGNED_STATUSES and sf_id and sf_id in cat_stats:
            cat_stats[sf_id]["total_products"] += 1
            if meta["is_active"]:
                cat_stats[sf_id]["active_products"] += 1
            else:
                cat_stats[sf_id]["inactive_products"] += 1
            if status == ResolutionStatus.MATCH.value:
                cat_stats[sf_id]["match_count"] += 1
            elif status == ResolutionStatus.OVERRIDE.value:
                cat_stats[sf_id]["override_count"] += 1
            elif status == ResolutionStatus.OVERRIDE_FALLBACK.value:
                cat_stats[sf_id]["override_fallback_count"] += 1

        if resolution is not None:
            for m in resolution.best_priority_matches:
                if m.rule_id in rule_stats:
                    rule_stats[m.rule_id]["matched_count"] += 1
                    if status == ResolutionStatus.CONFLICT.value:
                        rule_stats[m.rule_id]["conflict_count"] += 1
            for e in resolution.rule_errors:
                if e.rule_id in rule_stats:
                    rule_stats[e.rule_id]["error_count"] += 1
            for s in resolution.skipped_rules:
                if s.rule_id in rule_stats:
                    rule_stats[s.rule_id]["skipped_count"] += 1

        row = {
            **meta,
            "classification_status": status,
            "storefront_category_id": sf_id,
            "storefront_category_title": sf.title if sf is not None else None,
            "storefront_category_slug": sf.slug if sf is not None else None,
            "source": resolution.source.value if resolution is not None else None,
            "fingerprint": (
                resolution.fingerprint
                if resolution is not None
                else None
            ),
            "matched_rules": _matched_info_dicts(item),
            "conflicting_categories": (
                list(resolution.conflicting_category_ids)
                if resolution is not None
                else []
            ),
            "rule_errors": _rule_error_dicts(item),
            "skipped_rules": _skipped_dicts(item),
            "explanation": (
                resolution.explanation if resolution is not None else None
            ),
            "technical_error_type": item.error_type,
            "technical_error_message": item.error_message,
        }
        items.append(row)

    processed = sum(status_counts[k] for k in STATUS_COUNTER_KEYS)
    assigned_total = (
        status_counts["match"]
        + status_counts["override"]
        + status_counts["override_fallback"]
    )
    requires_attention = (
        status_counts["conflict"]
        + status_counts["unmatched"]
        + status_counts["needs_review"]
        + status_counts["error"]
    )

    elapsed_ms = int((time.perf_counter() - started_monotonic) * 1000)

    summary = {
        "total_products": total_products,
        "active_products": active_products,
        "inactive_products": inactive_products,
        "processed_products": processed,
        "match": status_counts["match"],
        "override": status_counts["override"],
        "override_fallback": status_counts["override_fallback"],
        "conflict": status_counts["conflict"],
        "unmatched": status_counts["unmatched"],
        "needs_review": status_counts["needs_review"],
        "error": status_counts["error"],
        "assigned_total": assigned_total,
        "requires_attention": requires_attention,
        "storefront_categories_total": len(storefront_categories),
        "active_rules": sum(1 for r in rules_orm if r.is_active),
        "inactive_rules": sum(1 for r in rules_orm if not r.is_active),
        "execution_time_ms": elapsed_ms,
    }

    if processed != total_products:
        diagnostics.append(
            f"processed_products ({processed}) != total_products ({total_products})."
        )

    categories_out: list[dict[str, Any]] = []
    for cat in storefront_categories:
        cid = str(cat.id)
        st = cat_stats[cid]
        pct = (
            round(100.0 * st["total_products"] / total_products, 4)
            if total_products > 0
            else 0.0
        )
        categories_out.append(
            {
                "id": cid,
                "title": cat.title,
                "slug": cat.slug,
                "parent_id": str(cat.parent_id) if cat.parent_id else None,
                "section_type": cat.section_type,
                "is_active": bool(cat.is_active),
                "total_products": st["total_products"],
                "active_products": st["active_products"],
                "inactive_products": st["inactive_products"],
                "match_count": st["match_count"],
                "override_count": st["override_count"],
                "override_fallback_count": st["override_fallback_count"],
                "percentage_of_catalog": pct,
            }
        )

    rules_out: list[dict[str, Any]] = []
    for rule in rules_orm:
        rid = str(rule.id)
        st = rule_stats[rid]
        target = rule.storefront_category
        rules_out.append(
            {
                "id": rid,
                "code": rule.code,
                "title": rule.title,
                "priority": rule.priority,
                "is_active": bool(rule.is_active),
                "target_category_id": str(target.id) if target is not None else None,
                "target_category_title": target.title if target is not None else None,
                "condition_type": rule.condition_type,
                "matched_count": st["matched_count"],
                "conflict_count": st["conflict_count"],
                "error_count": st["error_count"],
                "skipped_count": st["skipped_count"],
                "zero_match": st["matched_count"] == 0,
            }
        )

    problematic_items = [
        row for row in items if row["classification_status"] in PROBLEMATIC_STATUSES
    ]

    fingerprints = {
        "ruleset_fingerprint": batch.ruleset_fingerprint,
        "processed_products": processed,
        "stable_reorder_note": (
            "Классификация товара не зависит от порядка входа; "
            "items отсортированы по product_id."
        ),
    }

    metadata = {
        "report_version": REPORT_VERSION,
        "generated_at": _utc_now_iso(),
        "execution_time_ms": elapsed_ms,
        "data_source": "postgresql_orm",
        "mode": "dry_run",
        "loaded_products": total_products,
        "limit": limit,
        "limit_applied": limit is not None,
    }

    return {
        "summary": summary,
        "categories": categories_out,
        "items": items,
        "problematic_items": problematic_items,
        "rules": rules_out,
        "diagnostics": diagnostics,
        "fingerprints": fingerprints,
        "metadata": metadata,
    }


def run_storefront_dry_run(*, limit: int | None = None) -> dict[str, Any]:
    """
    Полный Dry-run по актуальной БД.

    limit — только для диагностики/тестов; отражается в metadata.
    По умолчанию — весь каталог Product.
    """
    started = time.perf_counter()
    diagnostics: list[str] = []
    if limit is not None:
        diagnostics.append(
            f"Применён диагностический limit={limit}; отчёт неполный относительно каталога."
        )

    products = _load_products(limit=limit)
    bundle, product_meta, rules_orm = _build_bundle(products)

    # Все витринные категории, включая пустые (один SELECT).
    storefront_categories = list(
        StorefrontCategory.objects.all().order_by("sort_order", "title", "id")
    )

    try:
        batch = classify_bundle(bundle)
    except Exception as exc:
        raise DryRunError(
            f"Критическая ошибка Classifier: {type(exc).__name__}: {exc}"
        ) from exc

    return _aggregate_report(
        batch=batch,
        product_meta=product_meta,
        rules_orm=rules_orm,
        storefront_categories=storefront_categories,
        diagnostics=diagnostics,
        limit=limit,
        started_monotonic=started,
    )


def format_summary_text(report: dict[str, Any]) -> str:
    """Человекочитаемая сводка для management command / stdout."""
    s = report["summary"]
    meta = report["metadata"]
    lines = [
        "Storefront taxonomy Dry-run",
        f"  mode: {meta.get('mode')}",
        f"  generated_at: {meta.get('generated_at')}",
        f"  execution_time_ms: {s.get('execution_time_ms')}",
        f"  limit: {meta.get('limit')}",
        "",
        f"  total_products: {s['total_products']} "
        f"(active={s['active_products']}, inactive={s['inactive_products']})",
        f"  processed_products: {s['processed_products']}",
        f"  match: {s['match']}",
        f"  override: {s['override']}",
        f"  override_fallback: {s['override_fallback']}",
        f"  conflict: {s['conflict']}",
        f"  unmatched: {s['unmatched']}",
        f"  needs_review: {s['needs_review']}",
        f"  error: {s['error']}",
        f"  assigned_total: {s['assigned_total']}",
        f"  requires_attention: {s['requires_attention']}",
        f"  storefront_categories_total: {s['storefront_categories_total']}",
        f"  rules: active={s['active_rules']}, inactive={s['inactive_rules']}",
        f"  ruleset_fingerprint: {report['fingerprints'].get('ruleset_fingerprint')}",
    ]
    diags = report.get("diagnostics") or []
    if diags:
        lines.append("")
        lines.append("  diagnostics:")
        for d in diags:
            lines.append(f"    - {d}")
    return "\n".join(lines)
