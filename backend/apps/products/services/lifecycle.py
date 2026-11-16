"""
Безопасное удаление / архивация товара (ONEC-023).

Hard-delete теряет Stock (исторически CASCADE) и резервы.
Предпочтительный путь — деактивация (is_active=False) с сохранением Stock / резервов.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.products.onec_protection import product_is_onec_managed


@dataclass(frozen=True)
class ProductDeleteDecision:
    """Результат попытки удалить товар через Admin API / Django Admin."""

    action: str  # "deactivated" | "deleted" | "blocked"
    product_id: str
    detail: str
    is_active: bool | None = None
    code: str | None = None


def product_has_stock(product) -> bool:
    return product.stock_items.exists()


def product_has_reserves(product) -> bool:
    return product.stock_items.filter(reserved_quantity__gt=0).exists()


def product_hard_delete_blocked(product) -> tuple[bool, str]:
    """
    True, если физическое удаление нарушит складскую целостность.
    Stock.product = PROTECT: при наличии остатков БД тоже не даст удалить.
    """
    if product_has_reserves(product):
        return True, "У товара есть активные резервы на складе."
    if product_has_stock(product):
        return True, "У товара есть складские остатки (Stock)."
    if product_is_onec_managed(product):
        return True, "Товар управляется 1С (onec_code); удаление запрещено."
    return False, ""


@transaction.atomic
def archive_product(product) -> ProductDeleteDecision:
    """Деактивировать товар, сохранив Stock / резервы / историю."""
    pid = str(product.pk)
    if product.is_active:
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        return ProductDeleteDecision(
            action="deactivated",
            product_id=pid,
            detail=(
                "Товар деактивирован. Складские остатки и резервы сохранены. "
                "Физическое удаление недоступно при наличии Stock или onec_code."
            ),
            is_active=False,
            code="product_deactivated",
        )
    return ProductDeleteDecision(
        action="deactivated",
        product_id=pid,
        detail="Товар уже деактивирован.",
        is_active=False,
        code="product_already_inactive",
    )


@transaction.atomic
def safe_delete_or_archive_product(product) -> ProductDeleteDecision:
    """
    Admin DELETE: сначала архивация; hard-delete только для локальных
    товаров без Stock / onec_code / резервов.
    """
    pid = str(product.pk)
    blocked, reason = product_hard_delete_blocked(product)

    if product.is_active:
        return archive_product(product)

    if blocked:
        return ProductDeleteDecision(
            action="blocked",
            product_id=pid,
            detail=(f"Удаление запрещено: {reason} " "Оставьте товар деактивированным."),
            is_active=False,
            code="product_delete_blocked",
        )

    product.delete()
    return ProductDeleteDecision(
        action="deleted",
        product_id=pid,
        detail="Товар удалён.",
        is_active=None,
        code=None,
    )
