"""
Классификация issues импорта 1С и сводка счётчиков для SyncLog (BLOCK 7).

Не смешивает: planned vs applied, errors vs warnings vs info, blockers.
"""

from __future__ import annotations

from typing import Any

# Информационные: не ошибка и не warning для статуса PARTIAL.
INFO_ISSUE_TYPES = frozenset(
    {
        "series_present",
    }
)

# Предупреждения: не блокируют APPLY (нет severity/blocker).
WARNING_ISSUE_TYPES = frozenset(
    {
        "rejected_price",
        "product_missing_price",
        "product_name_variants",
        "product_price_variants",
        "product_missing_category",
        "folder_missing_parent",
        "folder_duplicate_code",
        "category_slug_conflict",
        "product_sku_conflict",
    }
)


def classify_issue(issue: dict[str, Any]) -> str:
    """
    Возвращает: blocker | error | warning | info.

    blocker/error — критичные (severity/blocker или неизвестный серьёзный тип с severity).
    warning — не блокирует APPLY.
    info — справочно (series_present и т.п.).
    """
    if not isinstance(issue, dict):
        return "error"
    if issue.get("blocker") or issue.get("severity"):
        return "blocker"
    itype = (issue.get("type") or "").strip()
    if itype in INFO_ISSUE_TYPES:
        return "info"
    if itype in WARNING_ISSUE_TYPES:
        return "warning"
    # Неизвестный тип без severity — warning, чтобы не раздувать PARTIAL.
    return "warning"


def partition_issues(
    issues: list[dict[str, Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "blocker": [],
        "error": [],
        "warning": [],
        "info": [],
    }
    for issue in issues or []:
        if not isinstance(issue, dict):
            buckets["error"].append({"type": "invalid_issue", "message": str(issue)[:200]})
            continue
        kind = classify_issue(issue)
        if kind == "blocker":
            buckets["blocker"].append(issue)
        elif kind == "error":
            buckets["error"].append(issue)
        elif kind == "info":
            buckets["info"].append(issue)
        else:
            buckets["warning"].append(issue)
    return buckets


def issue_for_log(issue: dict[str, Any]) -> dict[str, Any]:
    """Компактная запись без секретов / полного XML."""
    return {
        "type": issue.get("type"),
        "class": classify_issue(issue),
        "onec_code": issue.get("onec_code") or "",
        "field": issue.get("field") or "",
        "value": str(issue.get("value") if issue.get("value") is not None else "")[:64],
        "reason": issue.get("reason") or "",
        "sklad_id": issue.get("sklad_id") or "",
        "message": (issue.get("message") or issue.get("notes") or str(issue))[:400],
    }


def build_issue_counts(partitioned: dict[str, list]) -> dict[str, int]:
    return {
        "blockers_count": len(partitioned.get("blocker") or []),
        "errors_count": len(partitioned.get("error") or [])
        + len(partitioned.get("blocker") or []),
        "warnings_count": len(partitioned.get("warning") or []),
        "info_count": len(partitioned.get("info") or []),
        "series_rows": sum(
            1
            for i in (partitioned.get("info") or [])
            if (i.get("type") or "") == "series_present"
        ),
    }
