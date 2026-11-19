"""
Сериализация Dry-run отчёта (S1.2.5).

Без ORM-объектов. Безопасный JSON: UUID / datetime / Decimal / Enum.
Без NaN/Infinity. UTF-8, ensure_ascii=False.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID


REPORT_VERSION = "1.0.0"


class ReportSerializationError(ValueError):
    """Не удалось безопасно сериализовать отчёт."""


def _reject_non_finite_float(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        raise ReportSerializationError(
            "JSON-отчёт не допускает NaN / Infinity."
        )
    return value


def json_default(obj: Any) -> Any:
    """Конвертер для json.dumps (без ORM)."""
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, float):
        return _reject_non_finite_float(obj)
    raise ReportSerializationError(
        f"Неподдерживаемый тип для JSON-отчёта: {type(obj).__name__}."
    )


def _sanitize(value: Any) -> Any:
    """Рекурсивная подготовка к сериализации (копия структуры)."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return _reject_non_finite_float(value)
    if isinstance(value, (UUID, Decimal, datetime, date, Enum, Path)):
        return json_default(value)
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    raise ReportSerializationError(
        f"Неподдерживаемый тип для JSON-отчёта: {type(value).__name__}."
    )


REQUIRED_TOP_KEYS = frozenset(
    {
        "summary",
        "categories",
        "items",
        "problematic_items",
        "rules",
        "diagnostics",
        "fingerprints",
        "metadata",
    }
)


def validate_report_structure(report: dict[str, Any]) -> None:
    """Базовая целостность ключей верхнего уровня."""
    if not isinstance(report, dict):
        raise ReportSerializationError("Отчёт должен быть dict.")
    missing = sorted(REQUIRED_TOP_KEYS - set(report.keys()))
    if missing:
        raise ReportSerializationError(
            f"В отчёте отсутствуют ключи: {', '.join(missing)}."
        )
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ReportSerializationError("summary должен быть dict.")
    for key in (
        "total_products",
        "processed_products",
        "match",
        "override",
        "override_fallback",
        "conflict",
        "unmatched",
        "needs_review",
        "error",
        "assigned_total",
        "requires_attention",
    ):
        if key not in summary:
            raise ReportSerializationError(f"summary.{key} обязателен.")


def serialize_dry_run_report(
    report: dict[str, Any],
    *,
    pretty: bool = False,
) -> str:
    """Сериализует отчёт в JSON-строку."""
    validate_report_structure(report)
    payload = _sanitize(report)
    if pretty:
        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
            default=json_default,
        )
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
        default=json_default,
    )


def dump_dry_run_report(
    report: dict[str, Any],
    path: str | Path,
    *,
    pretty: bool = True,
) -> Path:
    """
    Сохраняет JSON только по явно указанному пути.
    Создаёт родительские каталоги при необходимости.
    """
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    text = serialize_dry_run_report(report, pretty=pretty)
    target.write_text(text, encoding="utf-8")
    return target
