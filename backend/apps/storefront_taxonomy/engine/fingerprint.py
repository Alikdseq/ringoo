"""
Детерминированный fingerprint признаков и набора правил (S1.2.3 / S1.2.3.1).

Чистые функции без ORM. SHA-256 от канонического JSON.

S1.2.3.1: некорректный condition_payload больше не подменяется на {}.
Non-dict и schema-invalid dict кодируются tagged-представлением
с сохранением различий содержимого. Валидные dict сохраняют прежнюю
семантическую канонизацию (хеши валидных правил не меняются).
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Sequence

from apps.storefront_taxonomy.engine.errors import ConditionError
from apps.storefront_taxonomy.engine.normalizers import (
    NORMALIZER_VERSION,
    NormalizedFeatures,
    ProductFeatures,
    normalize_features,
)
from apps.storefront_taxonomy.engine.resolution_types import RuleInput
from apps.storefront_taxonomy.engine.schemas import (
    CONDITION_BRAND_EQUALS,
    CONDITION_COMPOSITE,
    CONDITION_ONEC_CATEGORY_PATH,
    CONDITION_ONEC_CATEGORY_SLUG,
    CONDITION_TITLE_CONTAINS,
    CONDITION_TITLE_REGEX,
    validate_condition_payload,
)

PAYLOAD_KIND_KEY = "__payload_kind__"


class FingerprintError(ValueError):
    """Не удалось детерминированно сериализовать значение для fingerprint."""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def canonicalize_for_fingerprint(value: Any) -> Any:
    """
    Рекурсивная канонизация с сохранением порядка списков:
    - dict: ключи будут отсортированы при json.dumps(sort_keys=True);
    - list/tuple: порядок элементов сохраняется.
    """
    if isinstance(value, dict):
        return {str(k): canonicalize_for_fingerprint(v) for k, v in value.items()}
    if isinstance(value, list):
        return [canonicalize_for_fingerprint(v) for v in value]
    if isinstance(value, tuple):
        return [canonicalize_for_fingerprint(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise FingerprintError(
                "float NaN/Inf нельзя детерминированно сериализовать для fingerprint."
            )
        return value
    if isinstance(value, str) or value is None:
        return value
    raise FingerprintError(
        f"Неподдерживаемый тип для fingerprint: {type(value).__name__}."
    )


def _is_schema_valid_payload(
    condition_type: str,
    payload: dict[str, Any],
    *,
    schema_version: int,
) -> bool:
    try:
        validate_condition_payload(
            condition_type,
            payload,
            schema_version=schema_version,
        )
        return True
    except ConditionError:
        return False


def tag_non_dict_payload(value: Any) -> dict[str, Any]:
    """Tagged representation для non-dict payload (без подмены на {})."""
    if value is None:
        return {PAYLOAD_KIND_KEY: "null"}
    if isinstance(value, bool):
        return {PAYLOAD_KIND_KEY: "bool", "value": value}
    if isinstance(value, int):
        return {PAYLOAD_KIND_KEY: "int", "value": value}
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise FingerprintError(
                "float NaN/Inf нельзя детерминированно сериализовать для fingerprint."
            )
        return {PAYLOAD_KIND_KEY: "float", "value": value}
    if isinstance(value, str):
        return {PAYLOAD_KIND_KEY: "str", "value": value}
    if isinstance(value, list):
        return {
            PAYLOAD_KIND_KEY: "list",
            "value": canonicalize_for_fingerprint(value),
        }
    if isinstance(value, tuple):
        return {
            PAYLOAD_KIND_KEY: "list",
            "value": canonicalize_for_fingerprint(list(value)),
        }
    raise FingerprintError(
        f"Неподдерживаемый тип condition_payload: {type(value).__name__}."
    )


def canonicalize_condition_payload(
    condition_type: str,
    payload: dict[str, Any],
    *,
    schema_version: int = 1,
) -> Any:
    """
    Семантическая канонизация валидного dict-payload (как в S1.2.3).

    Set-подобные массивы (contains/brands/slugs) сортируются.
    segments пути сохраняют порядок.
    Composite AND/OR siblings упорядочиваются по каноническому JSON.
    """
    if condition_type == CONDITION_COMPOSITE:
        return _canonicalize_composite_node(payload, schema_version=schema_version)

    data = canonicalize_for_fingerprint(payload)
    if not isinstance(data, dict):
        return data

    if condition_type == CONDITION_TITLE_CONTAINS and isinstance(data.get("contains"), list):
        data = {**data, "contains": sorted(str(x) for x in data["contains"])}
    elif condition_type == CONDITION_BRAND_EQUALS and isinstance(data.get("brands"), list):
        data = {**data, "brands": sorted(str(x) for x in data["brands"])}
    elif condition_type == CONDITION_ONEC_CATEGORY_SLUG and isinstance(
        data.get("slugs"), list
    ):
        data = {**data, "slugs": sorted(str(x) for x in data["slugs"])}
    elif condition_type == CONDITION_ONEC_CATEGORY_PATH:
        pass
    elif condition_type == CONDITION_TITLE_REGEX:
        pass
    return data


def encode_condition_payload_for_fingerprint(
    condition_type: str,
    payload: Any,
    *,
    schema_version: int = 1,
) -> Any:
    """
    Кодирует condition_payload для ruleset fingerprint.

    - non-dict → tagged kind (null/str/list/int/bool/float);
    - schema-valid dict → прежняя семантическая канонизация (без обёртки);
    - schema-invalid dict → tagged dict_invalid + order-preserving value.
    """
    if not isinstance(payload, dict):
        return tag_non_dict_payload(payload)

    if _is_schema_valid_payload(
        condition_type, payload, schema_version=schema_version
    ):
        return canonicalize_condition_payload(
            condition_type,
            payload,
            schema_version=schema_version,
        )

    return {
        PAYLOAD_KIND_KEY: "dict_invalid",
        "value": canonicalize_for_fingerprint(payload),
    }


def _encode_composite_leaf_payload(
    condition_type: str,
    node: dict[str, Any],
    *,
    schema_version: int,
) -> Any:
    """Кодирует payload leaf-узла composite без подмены на {}."""
    if "payload" not in node:
        return {PAYLOAD_KIND_KEY: "missing"}
    return encode_condition_payload_for_fingerprint(
        condition_type,
        node["payload"],
        schema_version=schema_version,
    )


def _canonicalize_composite_node(
    node: dict[str, Any],
    *,
    schema_version: int,
) -> Any:
    """
    Канонизация узла composite для валидного дерева.
    Leaf payload проходит через encode_… (valid → semantic; иначе tagged).
    """
    node = canonicalize_for_fingerprint(node)
    if not isinstance(node, dict):
        return node
    if "op" in node and isinstance(node.get("args"), list):
        args = [
            _canonicalize_composite_node(a, schema_version=schema_version)
            if isinstance(a, dict)
            else encode_condition_payload_for_fingerprint(
                CONDITION_COMPOSITE,
                a,
                schema_version=schema_version,
            )
            for a in node["args"]
        ]
        # AND/OR коммутативны → стабильный порядок siblings.
        # NOT: ровно один arg — сортировка безвредна.
        args_sorted = sorted(args, key=lambda a: _canonical_json_bytes(a).decode("utf-8"))
        return {"op": node["op"], "args": args_sorted}
    if "type" in node:
        ctype = str(node.get("type") or "")
        return {
            "type": ctype,
            "payload": _encode_composite_leaf_payload(
                ctype,
                node,
                schema_version=schema_version,
            ),
        }
    return node


def active_rules_for_fingerprint(rules: Sequence[RuleInput]) -> list[RuleInput]:
    """Только is_active=True; неактивные не влияют на ruleset fingerprint."""
    return [r for r in rules if r.is_active]


def ruleset_fingerprint(rules: Sequence[RuleInput]) -> str:
    """
    Версия/отпечаток активного набора правил.

    Учитывает: id, code, priority, condition_type, закодированный payload,
    schema_version, target category id + is_active (+ slug).
    Порядок входного списка не влияет (сортировка по code, затем id).
    """
    rows = []
    for rule in sorted(
        active_rules_for_fingerprint(rules),
        key=lambda r: (r.code, r.id),
    ):
        rows.append(
            {
                "id": rule.id,
                "code": rule.code,
                "priority": rule.priority,
                "condition_type": rule.condition_type,
                "condition_payload": encode_condition_payload_for_fingerprint(
                    rule.condition_type,
                    rule.condition_payload,
                    schema_version=rule.schema_version,
                ),
                "schema_version": rule.schema_version,
                "target_category": {
                    "id": rule.target_category.id,
                    "is_active": rule.target_category.is_active,
                    "slug": rule.target_category.slug,
                },
            }
        )
    return _sha256_hex({"rules": rows})


def features_fingerprint(
    features: ProductFeatures | NormalizedFeatures,
    *,
    normalizer_version: int | None = None,
) -> str:
    """
    Отпечаток признаков товара (+ NORMALIZER_VERSION).

    Не включает Product UUID, цену, остаток, рейтинг, updated_at.
    """
    if isinstance(features, NormalizedFeatures):
        norm = features
        ver = (
            normalizer_version
            if normalizer_version is not None
            else features.normalizer_version
        )
    else:
        ver = normalizer_version if normalizer_version is not None else NORMALIZER_VERSION
        norm = normalize_features(features)

    payload = {
        "normalizer_version": ver,
        "title": norm.title,
        "brand": norm.brand,
        "category_onec_code": norm.category_onec_code,
        "category_slug": norm.category_slug,
        "category_title_path": list(norm.category_title_path),
        "category_slug_path": list(norm.category_slug_path),
    }
    return _sha256_hex(payload)


def combine_classification_fingerprint(features_fp: str, ruleset_fp: str) -> str:
    """
    Единая точка composition classification fingerprint.

    Канонический JSON: {"features": <fp>, "ruleset": <fp>} + SHA-256.
    Не пересчитывает features/ruleset — только склеивает готовые отпечатки.
    """
    return _sha256_hex({"features": features_fp, "ruleset": ruleset_fp})


def classification_fingerprint(
    features: ProductFeatures | NormalizedFeatures,
    rules: Sequence[RuleInput],
    *,
    normalizer_version: int | None = None,
    features_fp: str | None = None,
    ruleset_fp: str | None = None,
) -> str:
    """
    Комбинированный fingerprint: признаки + активный ruleset.

    Опциональные features_fp / ruleset_fp позволяют переиспользовать
    уже вычисленные отпечатки без повторной нормализации / канонизации.
    Без kwargs семантика и результат идентичны S1.2.3 / S1.2.3.1.
    """
    ffp = (
        features_fp
        if features_fp is not None
        else features_fingerprint(features, normalizer_version=normalizer_version)
    )
    rfp = ruleset_fp if ruleset_fp is not None else ruleset_fingerprint(rules)
    return combine_classification_fingerprint(ffp, rfp)
