"""Сервисные операции над заказами (отмена, резерв)."""

from __future__ import annotations

import logging

from django.db import transaction

from apps.stores.models import Stock

from .models import Order

logger = logging.getLogger(__name__)


@transaction.atomic
def cancel_order_and_release_stock(order: Order, *, reason: str = "") -> Order:
    """
    Отменяет заказ и снимает резерв остатков по позициям.
    Идемпотентно: повторный вызов для уже cancelled только пытается
    снять резерв, если статус уже cancelled — статус не меняем повторно.
    """
    locked = Order.objects.select_for_update().prefetch_related("items").get(pk=order.pk)
    was_active = locked.status != Order.STATUS_CANCELLED
    if was_active:
        locked.status = Order.STATUS_CANCELLED
        locked.save(update_fields=["status", "updated_at"])
        logger.info(
            "Order %s cancelled%s",
            locked.order_number,
            f" ({reason})" if reason else "",
        )

    # Снимаем резерв при первой отмене. Повторный вызов не снимает повторно
    # (иначе можно «съесть» чужой резерв) — только если только что отменили.
    if was_active:
        for item in locked.items.all():
            if not item.product_id:
                continue
            Stock.release_for_delivery(item.product_id, item.quantity)

    return locked
