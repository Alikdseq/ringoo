"""
Classification Service (S1.2.4.2 / S1.2.4.3).

Чистый вычислительный слой: ClassificationInputBundle-like → результаты в памяти.
Без ORM, без HTTP, без записи в БД.

Соединяет: Fingerprint + Resolver. Не дублирует их алгоритмы.
S1.2.4.3: ruleset fp ×1 на batch; features/normalize ×1 на товар;
precomputed fingerprint в resolve; ClassifierError ⊄ ValueError.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from apps.storefront_taxonomy.engine.fingerprint import (
    FingerprintError,
    combine_classification_fingerprint,
    features_fingerprint,
    ruleset_fingerprint,
)
from apps.storefront_taxonomy.engine.normalizers import (
    ProductFeatures,
    normalize_features,
)
from apps.storefront_taxonomy.engine.resolution_types import (
    OverrideInput,
    ResolutionResult,
    RuleInput,
)
from apps.storefront_taxonomy.engine.resolver import resolve


class ClassifierError(Exception):
    """
    Структурная / фатальная ошибка входа Classifier (весь batch).

    Не наследует ValueError — не должна маскироваться item-level except ValueError.
    """


class ItemOutcome(str, Enum):
    """
    Технический исход элемента batch.

    Не смешивается с ResolutionStatus (бизнес-статусы Resolver).
    """

    RESOLVED = "resolved"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ClassificationItemResult:
    """
    Результат по одному товару.

    product_id — только корреляция с исходной записью;
    в fingerprint / conditions не входит.
    При outcome=RESOLVED поля resolution / fingerprints заполнены.
    При outcome=ERROR — error_* заполнены; business status отсутствует.
    """

    product_id: str
    outcome: ItemOutcome
    resolution: ResolutionResult | None = None
    features_fingerprint: str | None = None
    ruleset_fingerprint: str | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ClassificationBatchResult:
    """Пакетный результат classify_bundle."""

    ruleset_fingerprint: str
    items: tuple[ClassificationItemResult, ...]

    def by_product_id(self) -> dict[str, ClassificationItemResult]:
        return {item.product_id: item for item in self.items}


def _safe_error_message(exc: BaseException, *, limit: int = 400) -> str:
    text = f"{type(exc).__name__}: {exc}"
    text = text.replace("\n", " ").strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _require_mapping(value: Any, *, field: str) -> Mapping[Any, Any]:
    if not isinstance(value, Mapping):
        raise ClassifierError(
            f"Некорректный bundle: поле {field!r} должно быть mapping, "
            f"получено {type(value).__name__}."
        )
    return value


def _validate_bundle(bundle: Any) -> tuple[
    Mapping[str, ProductFeatures],
    Sequence[RuleInput],
    Mapping[str, OverrideInput],
]:
    """
    Структурная проверка входа.

    Duck-typing: совместим с adapters.ClassificationInputBundle
    без импорта adapters / Django в engine.
    """
    if bundle is None:
        raise ClassifierError("Некорректный bundle: None.")

    try:
        features_raw = bundle.features_by_product_id
        rules_raw = bundle.rules
        overrides_raw = bundle.overrides_by_product_id
    except AttributeError as exc:
        raise ClassifierError(
            "Некорректный bundle: отсутствуют обязательные поля "
            "features_by_product_id / rules / overrides_by_product_id."
        ) from exc

    features_map = _require_mapping(
        features_raw, field="features_by_product_id"
    )
    overrides_map = _require_mapping(
        overrides_raw, field="overrides_by_product_id"
    )

    if isinstance(rules_raw, (str, bytes)):
        raise ClassifierError(
            "Некорректный bundle: rules не может быть str/bytes."
        )
    if not isinstance(rules_raw, Sequence):
        raise ClassifierError(
            f"Некорректный bundle: rules должен быть Sequence, "
            f"получено {type(rules_raw).__name__}."
        )

    features: dict[str, ProductFeatures] = {}
    for key, value in features_map.items():
        features[str(key)] = value

    overrides: dict[str, OverrideInput] = {}
    for key, value in overrides_map.items():
        overrides[str(key)] = value

    return features, rules_raw, overrides


def _item_error(
    product_id: str,
    *,
    ruleset_fp: str | None,
    exc: BaseException,
) -> ClassificationItemResult:
    return ClassificationItemResult(
        product_id=product_id,
        outcome=ItemOutcome.ERROR,
        resolution=None,
        features_fingerprint=None,
        ruleset_fingerprint=ruleset_fp,
        error_type=type(exc).__name__,
        error_message=_safe_error_message(exc),
    )


def classify_bundle(bundle: Any) -> ClassificationBatchResult:
    """
    Классифицирует все товары из bundle.

    S1.2.4.3:
    - ruleset fingerprint — ровно 1 раз на batch;
    - normalize_features + features_fingerprint — ровно 1 раз на товар;
    - classification fingerprint через combine_* + resolve(..., fingerprint=);
    - NormalizedFeatures в resolve → без повторной normalize в conditions;
    - product_id только в ClassificationItemResult;
    - item-level ошибки → ItemOutcome.ERROR; ClassifierError → abort batch.
    """
    features_map, rules, overrides_map = _validate_bundle(bundle)

    try:
        ruleset_fp = ruleset_fingerprint(rules)
    except FingerprintError as exc:
        raise ClassifierError(
            f"Не удалось вычислить ruleset fingerprint для bundle: "
            f"{_safe_error_message(exc)}"
        ) from exc

    product_ids = sorted(features_map.keys())
    items: list[ClassificationItemResult] = []

    for product_id in product_ids:
        features = features_map[product_id]
        try:
            if not isinstance(features, ProductFeatures):
                raise TypeError(
                    f"features для product_id={product_id!r} должен быть "
                    f"ProductFeatures, получено {type(features).__name__}."
                )
            override = overrides_map.get(product_id)
            if override is not None and not isinstance(override, OverrideInput):
                raise TypeError(
                    f"override для product_id={product_id!r} должен быть "
                    f"OverrideInput, получено {type(override).__name__}."
                )

            norm = normalize_features(features)
            feat_fp = features_fingerprint(norm)
            clf_fp = combine_classification_fingerprint(feat_fp, ruleset_fp)
            resolution = resolve(
                norm,
                rules,
                override,
                fingerprint=clf_fp,
            )
        except ClassifierError:
            raise
        except FingerprintError as exc:
            items.append(
                _item_error(product_id, ruleset_fp=ruleset_fp, exc=exc)
            )
            continue
        except (TypeError, AttributeError, KeyError, ValueError) as exc:
            items.append(
                _item_error(product_id, ruleset_fp=ruleset_fp, exc=exc)
            )
            continue

        items.append(
            ClassificationItemResult(
                product_id=product_id,
                outcome=ItemOutcome.RESOLVED,
                resolution=resolution,
                features_fingerprint=feat_fp,
                ruleset_fingerprint=ruleset_fp,
                error_type=None,
                error_message=None,
            )
        )

    return ClassificationBatchResult(
        ruleset_fingerprint=ruleset_fp,
        items=tuple(items),
    )
