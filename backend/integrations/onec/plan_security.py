"""
Канонизация CatalogImportPlan и SHA-256 checksum (RELEASE 46.1 Stage D.1 / D.1.1).

Только вычисление отпечатка. Не защищает APPLY от подмены до этапов D.2+.

D.1.1:
- стабильная сортировка с JSON tie-breaker;
- явные типы без or "" / bool(x) / str(произвольное);
- Decimal нормализация без float;
- mode исключён из content-checksum (см. MODE_IN_CHECKSUM).
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import Enum
from typing import Any

from integrations.onec.importer import (
    CatalogImportPlan,
    CategoryAction,
    ProductAction,
    StockAction,
)

# Версия схемы канонического payload — bump при несовместимом изменении набора/правил.
CANONICAL_SCHEMA_VERSION = 2

# mode НЕ входит в content-checksum.
# DRY-RUN ставит mode=dry_run, APPLY — mode=apply (catalog_sync / plan_from_parsed).
# apply_catalog_import отдельно требует plan.mode=apply.
# Для D.2: хранить/сверять отпечаток содержимого без mode; mode проверять gate'ом APPLY.
MODE_IN_CHECKSUM = False


class PlanCanonicalizeError(ValueError):
    """Неподдерживаемый тип или некорректный план для канонизации."""


def _require_plan(plan: Any) -> CatalogImportPlan:
    if not isinstance(plan, CatalogImportPlan):
        raise PlanCanonicalizeError(
            f"Expected CatalogImportPlan, got {type(plan).__name__}"
        )
    return plan


def _decimal_to_canon_str(value: Decimal) -> str:
    """
    Нормализация Decimal → строка без float и без экспоненты.

    Правила:
    - format(..., "f") — фиксированная точка, точность сохраняется;
    - хвостовые нули после точки снимаются (10.50 и 10.5 → "10.5");
    - целая часть без точки (10.0 → "10");
    - -0 / -0.0 → "0";
    - Decimal("0.1")+Decimal("0.2") → "0.3".
    """
    if not isinstance(value, Decimal):
        raise PlanCanonicalizeError(
            f"Expected Decimal, got {type(value).__name__}"
        )
    if not value.is_finite():
        raise PlanCanonicalizeError("Non-finite Decimal is not allowed")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-0", "+0", "-"):
        return "0"
    if text.startswith("+"):
        text = text[1:]
    return text


def _jsonable(value: Any) -> Any:
    """
    Детерминированное JSON-совместимое представление.
    Не использует float, repr(), default=str.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return _decimal_to_canon_str(value)
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=lambda k: k if isinstance(k, str) else ""):
            if not isinstance(key, str):
                raise PlanCanonicalizeError(
                    f"Non-string dict key not allowed: {type(key).__name__}"
                )
            out[key] = _jsonable(value[key])
        return out
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    raise PlanCanonicalizeError(
        f"Unsupported type for plan canonicalization: {type(value).__name__}"
    )


def _req_str(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise PlanCanonicalizeError(
            f"{field} must be str, got {type(value).__name__}"
        )
    return value


def _opt_str(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise PlanCanonicalizeError(
        f"{field} must be str|None, got {type(value).__name__}"
    )


def _opt_bool(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise PlanCanonicalizeError(
        f"{field} must be bool|None, got {type(value).__name__}"
    )


def _dict_opt_str(data: dict[str, Any], key: str) -> str | None:
    if key not in data:
        return None
    return _opt_str(data[key], key)


def _dict_opt_bool(data: dict[str, Any], key: str) -> bool | None:
    if key not in data:
        return None
    return _opt_bool(data[key], key)


def _canon_json_text(value: Any) -> str:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sort_component(value: Any) -> tuple:
    """Компонент sort-key, различающий None / '' / False / 0."""
    if value is None:
        return (0, "")
    if isinstance(value, bool):
        return (1, 1 if value else 0)
    if isinstance(value, int) and not isinstance(value, bool):
        return (2, value)
    if isinstance(value, str):
        return (3, value)
    # Уже канонизированные элементы — только JSON-скаляры выше.
    raise PlanCanonicalizeError(
        f"Unsupported sort key type: {type(value).__name__}"
    )


def _stable_sorted(
    items: list[dict[str, Any]],
    primary_key,
) -> list[dict[str, Any]]:
    """
    Сортировка независимых списков:
    1) primary_key(item);
    2) полный canonical JSON элемента как tie-breaker.
    Порядок исходного списка не влияет при равных primary keys.
    """
    decorated: list[tuple[Any, str, dict[str, Any]]] = []
    for item in items:
        if not isinstance(item, dict):
            raise PlanCanonicalizeError(
                f"sorted list item must be dict, got {type(item).__name__}"
            )
        decorated.append((primary_key(item), _canon_json_text(item), item))
    decorated.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in decorated]


def _category_canon(action: CategoryAction) -> dict[str, Any]:
    # notes не читаются в apply_catalog_import.
    if not isinstance(action, CategoryAction):
        raise PlanCanonicalizeError("categories entry must be CategoryAction")
    return _jsonable(
        {
            "action": _req_str(action.action, "category.action"),
            "name": _req_str(action.name, "category.name"),
            "onec_code": _req_str(action.onec_code, "category.onec_code"),
            "parent_code": _req_str(action.parent_code, "category.parent_code"),
            "site_id": _opt_str(action.site_id, "category.site_id"),
            "site_slug": _opt_str(action.site_slug, "category.site_slug"),
        }
    )


def _product_canon(action: ProductAction) -> dict[str, Any]:
    # matched_by / notes / site_slug не читаются в apply_catalog_import
    # (slug создаётся из name|onec_code).
    if not isinstance(action, ProductAction):
        raise PlanCanonicalizeError("products entry must be ProductAction")
    return _jsonable(
        {
            "action": _req_str(action.action, "product.action"),
            "name": _req_str(action.name, "product.name"),
            "onec_code": _req_str(action.onec_code, "product.onec_code"),
            "parent_code": _req_str(action.parent_code, "product.parent_code"),
            "price": _opt_str(action.price, "product.price"),
            "site_id": _opt_str(action.site_id, "product.site_id"),
        }
    )


def _stock_canon(action: StockAction) -> dict[str, Any]:
    # quantity_status / notes не читаются в apply_catalog_import.
    if not isinstance(action, StockAction):
        raise PlanCanonicalizeError("stocks entry must be StockAction")
    return _jsonable(
        {
            "action": _req_str(action.action, "stock.action"),
            "onec_code": _req_str(action.onec_code, "stock.onec_code"),
            "quantity": _opt_str(action.quantity, "stock.quantity"),
            "series": _req_str(action.series, "stock.series"),
            "series_id": _req_str(action.series_id, "stock.series_id"),
            "site_product_id": _opt_str(
                action.site_product_id, "stock.site_product_id"
            ),
            "site_store_id": _opt_str(action.site_store_id, "stock.site_store_id"),
            "sklad": _req_str(action.sklad, "stock.sklad"),
            "sklad_id": _req_str(action.sklad_id, "stock.sklad_id"),
        }
    )


def _warehouse_canon(wh: Any) -> dict[str, Any]:
    if not isinstance(wh, dict):
        raise PlanCanonicalizeError(
            f"warehouse entry must be dict, got {type(wh).__name__}"
        )
    # apply читает sklad_id + sklad; None и "" различаем в checksum.
    return _jsonable(
        {
            "sklad": _dict_opt_str(wh, "sklad"),
            "sklad_id": _dict_opt_str(wh, "sklad_id"),
        }
    )


def _blocker_canon(blocker: Any) -> dict[str, Any]:
    if not isinstance(blocker, dict):
        raise PlanCanonicalizeError(
            f"apply_blocker must be dict, got {type(blocker).__name__}"
        )
    return _jsonable(
        {
            "message": _dict_opt_str(blocker, "message"),
            "onec_code": _dict_opt_str(blocker, "onec_code"),
            "sklad_id": _dict_opt_str(blocker, "sklad_id"),
            "type": _dict_opt_str(blocker, "type"),
        }
    )


def _issue_list_str_or_decimal(items: Any, field: str) -> list[str]:
    if not isinstance(items, (list, tuple)):
        raise PlanCanonicalizeError(f"{field} must be a list")
    out: list[str] = []
    for idx, item in enumerate(items):
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, Decimal):
            out.append(_decimal_to_canon_str(item))
        else:
            raise PlanCanonicalizeError(
                f"{field}[{idx}] must be str|Decimal, got {type(item).__name__}"
            )
    # Стабильная сортировка по canonical JSON элемента.
    return sorted(out, key=lambda s: _canon_json_text(s))


def _issue_value(value: Any) -> Any:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        raise PlanCanonicalizeError("issue.value must not be bool")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return _decimal_to_canon_str(value)
    raise PlanCanonicalizeError(
        f"issue.value unsupported type: {type(value).__name__}"
    )


def _issue_canon(issue: Any) -> dict[str, Any]:
    """
    Структурированные поля issue для целостности dry-run / gate blockers.
    """
    if not isinstance(issue, dict):
        raise PlanCanonicalizeError(f"issue must be dict, got {type(issue).__name__}")

    if "message" in issue:
        message = _opt_str(issue["message"], "issue.message")
    elif "notes" in issue:
        message = _opt_str(issue["notes"], "issue.notes")
    else:
        message = None

    payload: dict[str, Any] = {
        "blocker": _dict_opt_bool(issue, "blocker"),
        "field": _dict_opt_str(issue, "field"),
        "message": message,
        "name": _dict_opt_str(issue, "name"),
        "onec_code": _dict_opt_str(issue, "onec_code"),
        "parent_code": _dict_opt_str(issue, "parent_code"),
        "reason": _dict_opt_str(issue, "reason"),
        "series": _dict_opt_str(issue, "series"),
        "series_id": _dict_opt_str(issue, "series_id"),
        "severity": _dict_opt_bool(issue, "severity"),
        "sklad": _dict_opt_str(issue, "sklad"),
        "sklad_id": _dict_opt_str(issue, "sklad_id"),
        "type": _dict_opt_str(issue, "type"),
        "value": _issue_value(issue["value"]) if "value" in issue else None,
    }
    if "names" in issue and issue["names"] is not None:
        payload["names"] = _issue_list_str_or_decimal(issue["names"], "issue.names")
    if "prices" in issue and issue["prices"] is not None:
        payload["prices"] = _issue_list_str_or_decimal(issue["prices"], "issue.prices")
    return _jsonable(payload)


def _sort_key_product(item: dict[str, Any]) -> tuple:
    return (
        _sort_component(item.get("onec_code")),
        _sort_component(item.get("action")),
        _sort_component(item.get("site_id")),
    )


def _sort_key_stock(item: dict[str, Any]) -> tuple:
    return (
        _sort_component(item.get("onec_code")),
        _sort_component(item.get("sklad_id")),
        _sort_component(item.get("series_id")),
        _sort_component(item.get("action")),
        _sort_component(item.get("site_product_id")),
        _sort_component(item.get("site_store_id")),
    )


def _sort_key_warehouse(item: dict[str, Any]) -> tuple:
    return (
        _sort_component(item.get("sklad_id")),
        _sort_component(item.get("sklad")),
    )


def _sort_key_blocker(item: dict[str, Any]) -> tuple:
    return (
        _sort_component(item.get("type")),
        _sort_component(item.get("onec_code")),
        _sort_component(item.get("sklad_id")),
        _sort_component(item.get("message")),
    )


def _sort_key_issue(item: dict[str, Any]) -> tuple:
    return (
        _sort_component(item.get("type")),
        _sort_component(item.get("onec_code")),
        _sort_component(item.get("sklad_id")),
        _sort_component(item.get("field")),
        _sort_component(item.get("reason")),
        _sort_component(item.get("value")),
        _sort_component(item.get("parent_code")),
        _sort_component(item.get("series_id")),
        _sort_component(item.get("severity")),
        _sort_component(item.get("blocker")),
        _sort_component(item.get("message")),
    )


def canonicalize_catalog_plan(plan: CatalogImportPlan) -> dict[str, Any]:
    """
    Канонический dict плана для content-checksum.

    Включено всё, что влияет на apply_catalog_import (и gate blockers),
    плюс структурированные issues для целостности dry-run снимка.

    Исключено:
    - mode (MODE_IN_CHECKSUM=False): dry_run vs apply — intent gate, не содержимое;
      D.2 сверяет content-checksum, mode проверяет отдельно перед APPLY;
    - generated_at, run_id (волатильные ID запуска; run_id используется apply
      только как метка StockMovement, не как содержание плана);
    - summary / folder_count / product_row_count / unique_product_count;
    - notes / matched_by / quantity_status / product.site_slug
      (не читаются в apply_catalog_import);
    - reserved: в плане нет; apply не меняет reserved_quantity.

    categories: порядок СОХРАНЯЕТСЯ (топологический — parent resolve в apply).
    Остальные списки — стабильная сортировка + JSON tie-breaker.
    """
    plan = _require_plan(plan)

    categories = [_category_canon(c) for c in plan.categories]
    products = _stable_sorted(
        [_product_canon(p) for p in plan.products],
        _sort_key_product,
    )
    stocks = _stable_sorted(
        [_stock_canon(s) for s in plan.stocks],
        _sort_key_stock,
    )
    stocks_to_zero = _stable_sorted(
        [_stock_canon(s) for s in plan.stocks_to_zero],
        _sort_key_stock,
    )
    warehouses = _stable_sorted(
        [_warehouse_canon(w) for w in plan.warehouses],
        _sort_key_warehouse,
    )
    apply_blockers = _stable_sorted(
        [_blocker_canon(b) for b in plan.apply_blockers],
        _sort_key_blocker,
    )
    issues = _stable_sorted(
        [_issue_canon(i) for i in plan.issues],
        _sort_key_issue,
    )

    payload: dict[str, Any] = {
        "apply_blockers": apply_blockers,
        "categories": categories,
        "issues": issues,
        "products": products,
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "snapshot_policy": _req_str(plan.snapshot_policy, "snapshot_policy"),
        "source_folders_path": _req_str(
            plan.source_folders_path, "source_folders_path"
        ),
        "source_products_path": _req_str(
            plan.source_products_path, "source_products_path"
        ),
        "stocks": stocks,
        "stocks_to_zero": stocks_to_zero,
        "warehouses": warehouses,
    }
    if MODE_IN_CHECKSUM:
        payload["mode"] = _req_str(plan.mode, "mode")
    return _jsonable(payload)


def canonical_plan_json_bytes(plan: CatalogImportPlan) -> bytes:
    """UTF-8 JSON канонического payload (sort_keys, компактные separators)."""
    payload = canonicalize_catalog_plan(plan)
    text = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return text.encode("utf-8")


def catalog_plan_checksum(plan: CatalogImportPlan) -> str:
    """
    SHA-256 hex (lowercase, 64 символа) от канонического JSON плана.

    D.1/D.1.1: только отпечаток. Не подключает защиту APPLY.
    """
    digest = hashlib.sha256(canonical_plan_json_bytes(plan)).hexdigest()
    if len(digest) != 64:
        raise PlanCanonicalizeError(f"Unexpected digest length: {len(digest)}")
    return digest
