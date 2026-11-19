"""
Строгая валидация condition_payload (S1.2.2).

Неизвестные ключи отклоняются. Запрещённые Product UUID-ключи
проверяются рекурсивно (та же семантика, что в models S1.1).
"""

from __future__ import annotations

from typing import Any

from apps.storefront_taxonomy.engine.errors import (
    ExpressionLimitError,
    PayloadSchemaError,
    UnknownConditionTypeError,
    UnsupportedSchemaVersionError,
)
from apps.storefront_taxonomy.models import (
    _FORBIDDEN_CONDITION_PAYLOAD_KEYS,
    _find_forbidden_condition_keys,
)

SUPPORTED_SCHEMA_VERSIONS = frozenset({1})

COMPOSITE_MAX_DEPTH = 8
COMPOSITE_MAX_NODES = 64

MAX_PATTERN_LENGTH = 200
MAX_LIST_ITEMS = 32
MAX_STRING_LENGTH = 255
MAX_CONTAINS_STRING_LENGTH = 200

CONDITION_TITLE_CONTAINS = "title_contains"
CONDITION_TITLE_REGEX = "title_regex"
CONDITION_ONEC_CATEGORY_SLUG = "onec_category_slug"
CONDITION_ONEC_CATEGORY_PATH = "onec_category_path"
CONDITION_BRAND_EQUALS = "brand_equals"
CONDITION_COMPOSITE = "composite"

LEAF_CONDITION_TYPES = frozenset(
    {
        CONDITION_TITLE_CONTAINS,
        CONDITION_TITLE_REGEX,
        CONDITION_ONEC_CATEGORY_SLUG,
        CONDITION_ONEC_CATEGORY_PATH,
        CONDITION_BRAND_EQUALS,
    }
)

ALL_CONDITION_TYPES = LEAF_CONDITION_TYPES | {CONDITION_COMPOSITE}

COMPOSITE_OPS = frozenset({"and", "or", "not"})

PATH_SOURCES = frozenset({"title_path", "slug_path"})
PATH_MODES = frozenset({"exact", "prefix", "suffix", "contains_segment"})
SLUG_MODES = frozenset({"exact", "any_ancestor"})
CONTAINS_MATCH = frozenset({"any", "all"})


def _reject_forbidden_product_keys(payload: Any) -> None:
    forbidden = _find_forbidden_condition_keys(payload)
    if forbidden:
        raise PayloadSchemaError(
            "Универсальное правило не может ссылаться на Product UUID. "
            f"Запрещённые ключи: {', '.join(sorted(forbidden))}."
        )
    # Явная связь с константой модели (защита от расхождения при рефакторинге).
    assert _FORBIDDEN_CONDITION_PAYLOAD_KEYS


def _ensure_dict(payload: Any, *, label: str = "payload") -> dict:
    if not isinstance(payload, dict):
        raise PayloadSchemaError(f"{label} должен быть объектом JSON.")
    return payload


def _ensure_only_keys(data: dict, allowed: frozenset[str], *, label: str) -> None:
    unknown = set(data.keys()) - allowed
    if unknown:
        raise PayloadSchemaError(
            f"{label}: неизвестные ключи: {', '.join(sorted(unknown))}."
        )


def _ensure_nonempty_string_list(
    value: Any,
    *,
    key: str,
    max_items: int = MAX_LIST_ITEMS,
    max_len: int = MAX_STRING_LENGTH,
) -> list[str]:
    if not isinstance(value, list):
        raise PayloadSchemaError(f"{key} должен быть списком строк.")
    if not value:
        raise PayloadSchemaError(f"{key} не может быть пустым.")
    if len(value) > max_items:
        raise PayloadSchemaError(f"{key}: не более {max_items} элементов.")
    result: list[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise PayloadSchemaError(f"{key}[{i}] должен быть строкой.")
        if not item.strip():
            raise PayloadSchemaError(f"{key}[{i}] не может быть пустой строкой.")
        if len(item) > max_len:
            raise PayloadSchemaError(f"{key}[{i}]: длина > {max_len}.")
        result.append(item)
    return result


def validate_schema_version(schema_version: int) -> None:
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise UnsupportedSchemaVersionError(
            f"schema_version должен быть int, получено {type(schema_version).__name__}."
        )
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSchemaVersionError(
            f"Неподдерживаемая schema_version={schema_version}. "
            f"Допустимо: {sorted(SUPPORTED_SCHEMA_VERSIONS)}."
        )


def validate_title_contains_payload(payload: dict) -> dict:
    _ensure_only_keys(payload, frozenset({"contains", "match"}), label="title_contains")
    if "contains" not in payload:
        raise PayloadSchemaError("title_contains: обязателен ключ contains.")
    contains = _ensure_nonempty_string_list(
        payload["contains"],
        key="contains",
        max_len=MAX_CONTAINS_STRING_LENGTH,
    )
    match = payload.get("match", "any")
    if match not in CONTAINS_MATCH:
        raise PayloadSchemaError('title_contains.match: допустимо "any" или "all".')
    return {"contains": contains, "match": match}


def validate_title_regex_payload(payload: dict) -> dict:
    _ensure_only_keys(payload, frozenset({"pattern"}), label="title_regex")
    if "pattern" not in payload:
        raise PayloadSchemaError("title_regex: обязателен ключ pattern.")
    pattern = payload["pattern"]
    if not isinstance(pattern, str):
        raise PayloadSchemaError("title_regex.pattern должен быть строкой.")
    if not pattern:
        raise PayloadSchemaError("title_regex.pattern не может быть пустым.")
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise PayloadSchemaError(
            f"title_regex.pattern: длина > {MAX_PATTERN_LENGTH}."
        )
    return {"pattern": pattern}


def validate_onec_category_slug_payload(payload: dict) -> dict:
    _ensure_only_keys(payload, frozenset({"slugs", "mode"}), label="onec_category_slug")
    if "slugs" not in payload:
        raise PayloadSchemaError("onec_category_slug: обязателен ключ slugs.")
    slugs = _ensure_nonempty_string_list(payload["slugs"], key="slugs")
    mode = payload.get("mode", "exact")
    if mode not in SLUG_MODES:
        raise PayloadSchemaError(
            'onec_category_slug.mode: допустимо "exact" или "any_ancestor".'
        )
    return {"slugs": slugs, "mode": mode}


def validate_onec_category_path_payload(payload: dict) -> dict:
    _ensure_only_keys(
        payload,
        frozenset({"source", "segments", "mode"}),
        label="onec_category_path",
    )
    for key in ("source", "segments", "mode"):
        if key not in payload:
            raise PayloadSchemaError(f"onec_category_path: обязателен ключ {key}.")
    source = payload["source"]
    if source not in PATH_SOURCES:
        raise PayloadSchemaError(
            'onec_category_path.source: допустимо "title_path" или "slug_path".'
        )
    mode = payload["mode"]
    if mode not in PATH_MODES:
        raise PayloadSchemaError(
            "onec_category_path.mode: допустимо "
            "exact|prefix|suffix|contains_segment."
        )
    segments = _ensure_nonempty_string_list(payload["segments"], key="segments")
    return {"source": source, "segments": segments, "mode": mode}


def validate_brand_equals_payload(payload: dict) -> dict:
    _ensure_only_keys(payload, frozenset({"brands"}), label="brand_equals")
    if "brands" not in payload:
        raise PayloadSchemaError("brand_equals: обязателен ключ brands.")
    brands = _ensure_nonempty_string_list(
        payload["brands"],
        key="brands",
        max_len=100,
    )
    return {"brands": brands}


def _validate_composite_node(node: Any, *, depth: int, counter: list[int]) -> None:
    if depth > COMPOSITE_MAX_DEPTH:
        raise ExpressionLimitError(
            f"Превышена максимальная глубина composite ({COMPOSITE_MAX_DEPTH})."
        )
    counter[0] += 1
    if counter[0] > COMPOSITE_MAX_NODES:
        raise ExpressionLimitError(
            f"Превышено максимальное число узлов composite ({COMPOSITE_MAX_NODES})."
        )

    data = _ensure_dict(node, label="composite node")
    _reject_forbidden_product_keys(data)

    if "op" in data:
        _ensure_only_keys(data, frozenset({"op", "args"}), label="composite op")
        op = data["op"]
        if op not in COMPOSITE_OPS:
            raise PayloadSchemaError(f"Неизвестный оператор composite: {op!r}.")
        args = data.get("args")
        if not isinstance(args, list):
            raise PayloadSchemaError("composite.args должен быть списком.")
        if op == "not":
            if len(args) != 1:
                raise PayloadSchemaError("composite NOT требует ровно один аргумент.")
        elif len(args) < 1:
            raise PayloadSchemaError(
                f"composite {str(op).upper()} требует минимум один аргумент."
            )
        for child in args:
            _validate_composite_node(child, depth=depth + 1, counter=counter)
        return

    if "type" in data:
        _ensure_only_keys(data, frozenset({"type", "payload"}), label="composite leaf")
        ctype = data["type"]
        if ctype not in LEAF_CONDITION_TYPES:
            if ctype == CONDITION_COMPOSITE:
                raise PayloadSchemaError(
                    "Вложенный condition_type=composite запрещён; "
                    "используйте op/args."
                )
            raise UnknownConditionTypeError(f"Неизвестный тип условия: {ctype!r}.")
        if "payload" not in data:
            raise PayloadSchemaError("composite leaf: обязателен ключ payload.")
        leaf_payload = _ensure_dict(data["payload"], label="leaf payload")
        _reject_forbidden_product_keys(leaf_payload)
        validate_leaf_payload(ctype, leaf_payload)
        return

    raise PayloadSchemaError(
        "Узел composite должен содержать либо op/args, либо type/payload."
    )


def validate_leaf_payload(condition_type: str, payload: dict) -> dict:
    if condition_type == CONDITION_TITLE_CONTAINS:
        return validate_title_contains_payload(payload)
    if condition_type == CONDITION_TITLE_REGEX:
        return validate_title_regex_payload(payload)
    if condition_type == CONDITION_ONEC_CATEGORY_SLUG:
        return validate_onec_category_slug_payload(payload)
    if condition_type == CONDITION_ONEC_CATEGORY_PATH:
        return validate_onec_category_path_payload(payload)
    if condition_type == CONDITION_BRAND_EQUALS:
        return validate_brand_equals_payload(payload)
    raise UnknownConditionTypeError(f"Неизвестный тип условия: {condition_type!r}.")


def validate_condition_payload(
    condition_type: str,
    payload: Any,
    *,
    schema_version: int = 1,
) -> dict:
    """
    Полная валидация payload для condition_type.
    Возвращает нормализованную копию допустимых полей (leaf)
    или исходный dict для composite после проверки.
    """
    validate_schema_version(schema_version)

    if condition_type not in ALL_CONDITION_TYPES:
        raise UnknownConditionTypeError(f"Неизвестный тип условия: {condition_type!r}.")

    data = _ensure_dict(payload)
    _reject_forbidden_product_keys(data)

    if condition_type == CONDITION_COMPOSITE:
        counter = [0]
        _validate_composite_node(data, depth=1, counter=counter)
        return data

    return validate_leaf_payload(condition_type, data)
