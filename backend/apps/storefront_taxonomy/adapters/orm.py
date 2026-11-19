"""
ORM → DTO адаптер для storefront taxonomy (S1.2.4.1).

Читает Product / Category / ClassificationRule / StorefrontCategory /
ProductClassificationOverride и собирает структуры engine:
ProductFeatures, RuleInput, OverrideInput, CategoryRef.

Без write-операций, без вызова resolve/fingerprint.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID

from django.db.models import Prefetch

from apps.products.models import Category, Product
from apps.storefront_taxonomy.engine.normalizers import ProductFeatures
from apps.storefront_taxonomy.engine.resolution_types import (
    CategoryRef,
    OverrideInput,
    RuleInput,
)
from apps.storefront_taxonomy.models import (
    ClassificationRule,
    ProductClassificationOverride,
    StorefrontCategory,
    _find_forbidden_condition_keys,
)


class AdapterError(ValueError):
    """Контролируемая ошибка ORM-адаптера (повреждённые/недопустимые данные)."""


def _id_str(value: UUID | str) -> str:
    return str(value)


def storefront_category_to_ref(category: StorefrontCategory) -> CategoryRef:
    """StorefrontCategory → CategoryRef (без мутации ORM)."""
    return CategoryRef(
        id=_id_str(category.id),
        is_active=bool(category.is_active),
        slug=category.slug or "",
    )


def build_category_paths(
    category: Category,
    categories_by_id: Mapping[UUID | str, Category],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """
    Полный путь Category от корня к листу: titles и slugs.

    categories_by_id — заранее загруженное дерево (избегает N+1).
    Цикл parent или отсутствующий parent → AdapterError.
    """
    chain: list[Category] = []
    seen: set[str] = set()
    current: Category | None = category

    while current is not None:
        cid = _id_str(current.id)
        if cid in seen:
            raise AdapterError(
                f"Обнаружен цикл в иерархии Category (id={cid})."
            )
        seen.add(cid)
        chain.append(current)
        parent_id = current.parent_id
        if not parent_id:
            break
        parent = categories_by_id.get(parent_id) or categories_by_id.get(
            _id_str(parent_id)
        )
        if parent is None:
            raise AdapterError(
                f"Отсутствует родительская Category id={parent_id} "
                f"для category id={cid}."
            )
        current = parent

    chain.reverse()
    title_path = tuple(c.title for c in chain)
    slug_path = tuple(c.slug for c in chain)
    return title_path, slug_path


def product_to_features(
    product: Product,
    *,
    categories_by_id: Mapping[UUID | str, Category] | None = None,
) -> ProductFeatures:
    """
    Product → ProductFeatures.

    Product.id / UUID не включаются.
    Исходная Category.is_active не фильтрует путь (признаки для match as-is).
    """
    category = getattr(product, "category", None)
    if category is None:
        if product.category_id:
            raise AdapterError(
                f"Product id={product.id}: category_id={product.category_id} "
                "задана, но объект Category не загружен/отсутствует."
            )
        return ProductFeatures(
            title=product.title or "",
            brand=product.brand,
            category_slug="",
            category_onec_code=None,
            category_title_path=(),
            category_slug_path=(),
        )

    cat_map = categories_by_id
    if cat_map is None:
        # Одиночная загрузка: один запрос на всё дерево категорий.
        cat_map = {c.id: c for c in Category.objects.all()}

    # Гарантируем наличие самой category в map.
    if category.id not in cat_map and _id_str(category.id) not in cat_map:
        cat_map = dict(cat_map)
        cat_map[category.id] = category

    title_path, slug_path = build_category_paths(category, cat_map)
    return ProductFeatures(
        title=product.title or "",
        brand=product.brand,
        category_slug=category.slug or "",
        category_onec_code=category.onec_code,
        category_title_path=title_path,
        category_slug_path=slug_path,
    )


def _copy_payload(payload: Any) -> Any:
    """Глубокая копия payload без мутации ORM JSONField."""
    return copy.deepcopy(payload)


def rule_to_input(rule: ClassificationRule) -> RuleInput:
    """
    ClassificationRule → RuleInput.

    Payload копируется as-is (типы сохраняются).
    Запрещённые Product UUID-ключи → AdapterError (не strip).
    """
    payload = _copy_payload(rule.condition_payload)
    # Рекурсивный обход dict/list любого уровня (в т.ч. top-level list).
    # Скаляры / иные типы JSON-значений ключей не содержат — helper
    # их пропускает без преобразования.
    forbidden = _find_forbidden_condition_keys(payload)
    if forbidden:
        raise AdapterError(
            f"ClassificationRule code={rule.code}: payload содержит "
            f"запрещённые ключи Product UUID: {', '.join(sorted(forbidden))}."
        )
    # Non-dict payload без forbidden keys передаём as-is (fingerprint tagged);
    # RuleInput аннотирован dict, но runtime допускает для целостности fp.
    target = rule.storefront_category
    if target is None:
        raise AdapterError(
            f"ClassificationRule code={rule.code}: storefront_category отсутствует."
        )
    return RuleInput(
        id=_id_str(rule.id),
        code=rule.code,
        priority=int(rule.priority),
        is_active=bool(rule.is_active),
        condition_type=rule.condition_type,
        condition_payload=payload,  # type: ignore[arg-type]
        schema_version=int(rule.schema_version),
        target_category=storefront_category_to_ref(target),
    )


def override_to_input(override: ProductClassificationOverride) -> OverrideInput:
    """ProductClassificationOverride → OverrideInput."""
    target = override.storefront_category
    if target is None:
        raise AdapterError(
            f"Override id={override.id}: storefront_category отсутствует."
        )
    return OverrideInput(
        category=storefront_category_to_ref(target),
        is_locked=bool(override.is_locked),
        reason=override.reason,
    )


def load_category_map() -> dict[UUID, Category]:
    """Один SELECT всех Category для построения путей без N+1."""
    return {c.id: c for c in Category.objects.all()}


def load_rules(*, active_only: bool = False) -> tuple[RuleInput, ...]:
    """
    Загрузка правил с select_related(storefront_category).

    Сортировка детерминированная: priority ASC, code ASC, id ASC.
    active_only=False — передаёт и inactive (Resolver сам skip'ает).
    """
    qs = ClassificationRule.objects.select_related("storefront_category").order_by(
        "priority", "code", "id"
    )
    if active_only:
        qs = qs.filter(is_active=True)
    return tuple(rule_to_input(rule) for rule in qs)


def load_overrides_for_products(
    product_ids: Sequence[UUID | str],
) -> dict[str, OverrideInput]:
    """
    Overrides для набора Product (один запрос + select_related category).
    Ключ — str(product_id).
    """
    if not product_ids:
        return {}
    ids = list(product_ids)
    qs = ProductClassificationOverride.objects.select_related(
        "storefront_category"
    ).filter(product_id__in=ids)
    result: dict[str, OverrideInput] = {}
    for ov in qs:
        result[_id_str(ov.product_id)] = override_to_input(ov)
    return result


@dataclass(frozen=True, slots=True)
class ClassificationInputBundle:
    """
    Пакет входных данных для будущего Classifier (без решений).

    product_id используется только как ключ корреляции batch;
    в ProductFeatures / fingerprint / conditions не входит.
    """

    features_by_product_id: dict[str, ProductFeatures]
    rules: tuple[RuleInput, ...]
    overrides_by_product_id: dict[str, OverrideInput]


def load_classification_bundle(
    *,
    product_ids: Iterable[UUID | str] | None = None,
    active_rules_only: bool = False,
) -> ClassificationInputBundle:
    """
    Пакетная загрузка без N+1:

    1. Category.objects.all() — карта дерева;
    2. Product (+ select_related category);
    3. ClassificationRule (+ select_related storefront_category);
    4. Overrides для выбранных product_id (+ select_related).
    """
    categories_by_id = load_category_map()

    product_qs = Product.objects.select_related("category").order_by("id")
    if product_ids is not None:
        product_qs = product_qs.filter(id__in=list(product_ids))

    features_by_product_id: dict[str, ProductFeatures] = {}
    loaded_ids: list[str] = []
    for product in product_qs:
        pid = _id_str(product.id)
        features_by_product_id[pid] = product_to_features(
            product, categories_by_id=categories_by_id
        )
        loaded_ids.append(pid)

    rules = load_rules(active_only=active_rules_only)
    overrides = load_overrides_for_products(loaded_ids)

    return ClassificationInputBundle(
        features_by_product_id=features_by_product_id,
        rules=rules,
        overrides_by_product_id=overrides,
    )


# Prefetch helper для внешних вызовов (не обязателен для bundle).
def products_queryset_for_adapter():
    return Product.objects.select_related("category").prefetch_related(
        Prefetch(
            "storefront_override",
            queryset=ProductClassificationOverride.objects.select_related(
                "storefront_category"
            ),
        )
    )
