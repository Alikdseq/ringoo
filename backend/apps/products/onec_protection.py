"""
Защита полей товара, которыми управляет 1С (есть onec_code).

Локальные поля Ringoo (SEO, описания, публикация) остаются редактируемыми.
"""

from __future__ import annotations

from typing import Iterable

from rest_framework import serializers

# Поля, которые импортёр 1С создаёт/обновляет для номенклатуры с onec_code.
ONEC_MANAGED_PRODUCT_FIELDS = frozenset(
    {
        "title",
        "sku",
        "price",
        "old_price",
        "category",
        "onec_code",
        "onec_type",
    }
)

# Локальные поля витрины — всегда можно править через Admin API.
RINGOO_LOCAL_PRODUCT_FIELDS = frozenset(
    {
        "slug",
        "description",
        "short_description",
        "meta_title",
        "meta_description",
        "is_active",
        "is_featured",
        "brand",
    }
)


def product_is_onec_managed(product) -> bool:
    code = getattr(product, "onec_code", None)
    return bool(code and str(code).strip())


def reject_onec_managed_writes(
    product,
    incoming_fields: Iterable[str],
    *,
    label: str = "товар",
) -> None:
    """
    Если у product есть onec_code — запретить изменение ONEC_MANAGED_PRODUCT_FIELDS.
    Выбрасывает ValidationError с понятным списком полей.
    """
    if not product_is_onec_managed(product):
        return
    blocked = sorted(
        {f for f in incoming_fields if f in ONEC_MANAGED_PRODUCT_FIELDS}
    )
    if not blocked:
        return
    raise serializers.ValidationError(
        {
            "detail": (
                f"Поля {', '.join(blocked)} управляются 1С и недоступны для "
                f"ручного изменения у {label} с onec_code="
                f"{getattr(product, 'onec_code', '')}."
            ),
            "code": "onec_managed_fields_readonly",
            "fields": blocked,
            "onec_code": getattr(product, "onec_code", "") or "",
        }
    )
