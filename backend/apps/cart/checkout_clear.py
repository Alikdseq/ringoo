"""
Очистка корзины после достоверно оплаченного online-заказа.

Не удаляет всю корзину целиком: вычитает количества по позициям OrderItem,
учитывая product + color + store заказа (FUNC-004 / FUNC-011).
Идемпотентно: повторный вызов безопасен (checkout_cart_id → None).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.orders.models import Order

logger = logging.getLogger(__name__)


def _line_key(*, product_id, color_id, store_id) -> tuple:
    return (str(product_id), str(color_id) if color_id else "", str(store_id) if store_id else "")


def clear_cart_after_successful_payment(order: "Order") -> dict:
    """
    Вычитает из привязанной корзины количества, соответствующие оплаченному заказу.
    Сопоставление: product + color (+ store заказа как точка комплектации).
    """
    from apps.cart.models import Cart, CartItem
    from apps.orders.models import OrderItem

    report: dict = {
        "order_id": str(order.pk),
        "cart_id": None,
        "deleted_rows": 0,
        "qty_removed": 0,
        "already_cleared": False,
        "skipped_foreign": False,
        "cart_missing": False,
    }

    logger.info(
        "cart_clear_started order_id=%s checkout_cart_id=%s",
        order.pk,
        getattr(order, "checkout_cart_id", None),
    )

    with transaction.atomic():
        locked = (
            type(order)
            .objects.select_for_update()
            .only("id", "checkout_cart_id", "user_id", "payment_type", "store_id")
            .get(pk=order.pk)
        )

        cart_id = locked.checkout_cart_id
        report["cart_id"] = str(cart_id) if cart_id else None

        if cart_id is None:
            report["already_cleared"] = True
            logger.info(
                "cart_clear_completed order_id=%s already_cleared=1",
                locked.pk,
            )
            return report

        cart = (
            Cart.objects.select_for_update()
            .filter(pk=cart_id)
            .only("id", "user_id", "session_key")
            .first()
        )
        if cart is None:
            type(order).objects.filter(pk=locked.pk).update(checkout_cart_id=None)
            report["cart_missing"] = True
            report["already_cleared"] = True
            logger.info(
                "cart_clear_completed order_id=%s cart_missing=1",
                locked.pk,
            )
            return report

        if locked.user_id and cart.user_id and cart.user_id != locked.user_id:
            type(order).objects.filter(pk=locked.pk).update(checkout_cart_id=None)
            report["skipped_foreign"] = True
            logger.warning(
                "cart_clear_failed order_id=%s reason=foreign_cart cart_id=%s "
                "order_user=%s cart_user=%s",
                locked.pk,
                cart_id,
                locked.user_id,
                cart.user_id,
            )
            return report

        order_store_id = locked.store_id
        qty_by_key: dict[tuple, int] = defaultdict(int)
        for row in OrderItem.objects.filter(order_id=locked.pk).only(
            "product_id", "color_id", "quantity"
        ):
            if row.product_id:
                key = _line_key(
                    product_id=row.product_id,
                    color_id=row.color_id,
                    store_id=order_store_id,
                )
                qty_by_key[key] += int(row.quantity)

        deleted_rows = 0
        qty_removed = 0

        for key, need in qty_by_key.items():
            product_id, color_id, store_id = key
            remaining = need
            qs = CartItem.objects.select_for_update().filter(
                cart_id=cart.pk, product_id=product_id
            )
            if color_id:
                qs = qs.filter(color_id=color_id)
            else:
                qs = qs.filter(color__isnull=True)
            if store_id:
                # Предпочитаем строки того же магазина; если нет — любые того же product+color
                preferred = list(qs.filter(store_id=store_id).order_by("created_at"))
                fallback = list(
                    qs.exclude(store_id=store_id).order_by("created_at")
                ) if not preferred else []
                lines = preferred + fallback
            else:
                lines = list(qs.order_by("created_at"))

            for line in lines:
                if remaining <= 0:
                    break
                if line.quantity <= remaining:
                    take = line.quantity
                    remaining -= take
                    qty_removed += take
                    line.delete()
                    deleted_rows += 1
                else:
                    line.quantity -= remaining
                    qty_removed += remaining
                    line.save(update_fields=["quantity", "updated_at"])
                    remaining = 0

        report["deleted_rows"] = deleted_rows
        report["qty_removed"] = qty_removed

        type(order).objects.filter(pk=locked.pk).update(checkout_cart_id=None)

    logger.info(
        "cart_clear_completed order_id=%s cart_id=%s deleted_rows=%s qty_removed=%s",
        report["order_id"],
        report["cart_id"],
        report["deleted_rows"],
        report["qty_removed"],
    )
    return report
