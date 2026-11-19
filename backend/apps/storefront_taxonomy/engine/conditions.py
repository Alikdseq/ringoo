"""
Сопоставление условий ClassificationRule (S1.2.2).

Matcher получает уже подготовленные ProductFeatures / NormalizedFeatures
и не обращается к БД.

Regex: стандартный модуль ``re`` без timeout. Безопасность — fail-closed
эвристики (длина + вложенные квантификаторы). Библиотека с timeout
в зависимостях проекта отсутствует; новые зависимости не добавляются.
"""

from __future__ import annotations

import re
from typing import Any

from apps.storefront_taxonomy.engine.errors import (
    ConditionError,
    ConditionEvalError,
    ExpressionLimitError,
    InvalidRegexError,
    PayloadSchemaError,
    UnknownConditionTypeError,
    UnsafeRegexError,
    UnsupportedSchemaVersionError,
)
from apps.storefront_taxonomy.engine.normalizers import (
    NormalizedFeatures,
    ProductFeatures,
    normalize_brand,
    normalize_features,
    normalize_path_segments,
    normalize_slug,
    normalize_slug_path,
    normalize_text,
)
from apps.storefront_taxonomy.engine.schemas import (
    COMPOSITE_MAX_DEPTH,
    COMPOSITE_MAX_NODES,
    CONDITION_BRAND_EQUALS,
    CONDITION_COMPOSITE,
    CONDITION_ONEC_CATEGORY_PATH,
    CONDITION_ONEC_CATEGORY_SLUG,
    CONDITION_TITLE_CONTAINS,
    CONDITION_TITLE_REGEX,
    validate_condition_payload,
)

__all__ = [
    "ConditionError",
    "PayloadSchemaError",
    "UnknownConditionTypeError",
    "InvalidRegexError",
    "UnsafeRegexError",
    "UnsupportedSchemaVersionError",
    "ExpressionLimitError",
    "ConditionEvalError",
    "validate_condition",
    "match_condition",
]


# Вложенные квантификаторы вида (a+)+, (a*)*, (foo+)?, (a+){2,} —
# типичный источник катастрофического backtracking в stdlib re.
_NESTED_QUANTIFIER_RE = re.compile(
    r"\([^()]*[+*][^()]*\)[+*?]"
    r"|\([^()]*[+*][^()]*\)\{\d*,?\d*\}"
)


def _assert_regex_safe(pattern: str) -> None:
    """
    Fail-closed проверка без timeout (stdlib ``re`` timeout не поддерживает).

    Отклоняет паттерны с признаками nested quantifiers.
    Длина уже ограничена схемой (MAX_PATTERN_LENGTH).
    """
    if _NESTED_QUANTIFIER_RE.search(pattern):
        raise UnsafeRegexError(
            "Регулярное выражение отклонено: обнаружены вложенные квантификаторы "
            "(риск катастрофического backtracking). "
            "stdlib re не предоставляет timeout; безопасный match невозможен."
        )


def _compile_title_regex(pattern: str) -> re.Pattern[str]:
    _assert_regex_safe(pattern)
    try:
        return re.compile(pattern, re.IGNORECASE | re.UNICODE)
    except re.error as exc:
        raise InvalidRegexError(f"Некорректное регулярное выражение: {exc}") from exc


def _preflight_regex_in_payload(condition_type: str, payload: dict) -> None:
    """Компиляция/safety regex на этапе validate (до match)."""
    if condition_type == CONDITION_TITLE_REGEX:
        _compile_title_regex(payload["pattern"])
        return
    if condition_type != CONDITION_COMPOSITE:
        return

    def walk(node: dict) -> None:
        if "op" in node:
            for child in node["args"]:
                walk(child)
            return
        if node.get("type") == CONDITION_TITLE_REGEX:
            _compile_title_regex(node["payload"]["pattern"])

    walk(payload)


def _as_normalized(
    features: ProductFeatures | NormalizedFeatures,
) -> NormalizedFeatures:
    if isinstance(features, NormalizedFeatures):
        return features
    return normalize_features(features)


def validate_condition(
    condition_type: str,
    payload: Any,
    *,
    schema_version: int = 1,
) -> dict:
    """
    Валидирует payload до match (схема + regex safety/compile).
    Поднимает ConditionError и подклассы.
    """
    validated = validate_condition_payload(
        condition_type,
        payload,
        schema_version=schema_version,
    )
    _preflight_regex_in_payload(condition_type, validated)
    return validated


def _match_title_contains(payload: dict, features: NormalizedFeatures) -> bool:
    needles = [normalize_text(x) for x in payload["contains"]]
    mode = payload.get("match", "any")
    title = features.title
    if mode == "all":
        return all(n in title for n in needles)
    return any(n in title for n in needles)


def _match_title_regex(payload: dict, features: NormalizedFeatures) -> bool:
    compiled = _compile_title_regex(payload["pattern"])
    try:
        return compiled.search(features.title) is not None
    except re.error as exc:
        raise ConditionEvalError(f"Ошибка выполнения regex: {exc}") from exc


def _match_onec_category_slug(payload: dict, features: NormalizedFeatures) -> bool:
    targets = {normalize_slug(s) for s in payload["slugs"]}
    mode = payload.get("mode", "exact")
    if mode == "exact":
        return bool(features.category_slug) and features.category_slug in targets
    path = features.category_slug_path
    if not path and features.category_slug:
        path = (features.category_slug,)
    return any(seg in targets for seg in path)


def _match_onec_category_path(payload: dict, features: NormalizedFeatures) -> bool:
    source = payload["source"]
    mode = payload["mode"]
    if source == "title_path":
        haystack = features.category_title_path
        needle = normalize_path_segments(payload["segments"])
    else:
        haystack = features.category_slug_path
        needle = normalize_slug_path(payload["segments"])

    if not needle:
        return False

    if mode == "exact":
        return haystack == needle
    if mode == "prefix":
        if len(needle) > len(haystack):
            return False
        return haystack[: len(needle)] == needle
    if mode == "suffix":
        if len(needle) > len(haystack):
            return False
        return haystack[-len(needle) :] == needle
    if mode == "contains_segment":
        hayset = set(haystack)
        return all(seg in hayset for seg in needle)
    raise ConditionEvalError(f"Неизвестный mode path: {mode!r}")


def _match_brand_equals(payload: dict, features: NormalizedFeatures) -> bool:
    if not features.brand:
        return False
    targets = {normalize_brand(b) for b in payload["brands"]}
    return features.brand in targets


def _eval_composite_node(
    node: dict,
    features: NormalizedFeatures,
    *,
    depth: int,
    counter: list[int],
) -> bool:
    if depth > COMPOSITE_MAX_DEPTH:
        raise ExpressionLimitError(
            f"Превышена максимальная глубина composite ({COMPOSITE_MAX_DEPTH})."
        )
    counter[0] += 1
    if counter[0] > COMPOSITE_MAX_NODES:
        raise ExpressionLimitError(
            f"Превышено максимальное число узлов composite ({COMPOSITE_MAX_NODES})."
        )

    if "op" in node:
        op = node["op"]
        args = node["args"]
        if op == "and":
            return all(
                _eval_composite_node(a, features, depth=depth + 1, counter=counter)
                for a in args
            )
        if op == "or":
            return any(
                _eval_composite_node(a, features, depth=depth + 1, counter=counter)
                for a in args
            )
        if op == "not":
            return not _eval_composite_node(
                args[0], features, depth=depth + 1, counter=counter
            )
        raise ConditionEvalError(f"Неизвестный оператор: {op!r}")

    ctype = node["type"]
    leaf_payload = validate_condition_payload(ctype, node["payload"], schema_version=1)
    return _match_leaf(ctype, leaf_payload, features)


def _match_leaf(
    condition_type: str,
    payload: dict,
    features: NormalizedFeatures,
) -> bool:
    if condition_type == CONDITION_TITLE_CONTAINS:
        return _match_title_contains(payload, features)
    if condition_type == CONDITION_TITLE_REGEX:
        return _match_title_regex(payload, features)
    if condition_type == CONDITION_ONEC_CATEGORY_SLUG:
        return _match_onec_category_slug(payload, features)
    if condition_type == CONDITION_ONEC_CATEGORY_PATH:
        return _match_onec_category_path(payload, features)
    if condition_type == CONDITION_BRAND_EQUALS:
        return _match_brand_equals(payload, features)
    raise UnknownConditionTypeError(f"Неизвестный тип условия: {condition_type!r}.")


def match_condition(
    condition_type: str,
    payload: Any,
    features: ProductFeatures | NormalizedFeatures,
    *,
    schema_version: int = 1,
) -> bool:
    """
    Валидирует payload и возвращает True/False.

    Контролируемые ошибки схемы/regex поднимаются как исключения
    (не маскируются в False). Вызывающий слой (resolver, S1.2.3)
    должен ловить ConditionError per-rule.
    """
    validated = validate_condition(
        condition_type,
        payload,
        schema_version=schema_version,
    )
    norm = _as_normalized(features)

    if condition_type == CONDITION_COMPOSITE:
        return _eval_composite_node(
            validated,
            norm,
            depth=1,
            counter=[0],
        )
    return _match_leaf(condition_type, validated, norm)
