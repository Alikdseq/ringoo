"""Сервисные операции над заказами (отмена, резерв, обезличивание)."""

from __future__ import annotations

import logging

from django.db import transaction

from apps.orders.models import Order

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
        from integrations.onec.orders import release_order_item_reservations

        release_order_item_reservations(locked)

        order_pk = locked.pk

        def _enqueue_onec_cancel():
            from apps.orders.tasks import enqueue_order_cancel

            enqueue_order_cancel(order_pk)

        transaction.on_commit(_enqueue_onec_cancel)

    return locked
