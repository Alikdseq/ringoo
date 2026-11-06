"""
Единый FSM переходов статуса заказа (INT-001 / INT-002).

Все бизнес-значимые смены статуса должны идти через transition_order_status
или cancel_order_and_release_stock.
"""

from __future__ import annotations

import logging

from django.db import transaction

from apps.orders.models import Order

logger = logging.getLogger(__name__)


class OrderTransitionError(Exception):
    def __init__(self, message: str, *, code: str = "invalid_transition"):
        self.message = message
        self.code = code
        super().__init__(message)


# Исходный → допустимые целевые (кроме cancel — через cancel_order_and_release_stock)
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    Order.STATUS_NEW: frozenset(
        {Order.STATUS_CONFIRMED, Order.STATUS_CANCELLED}
    ),
    Order.STATUS_CONFIRMED: frozenset(
        {Order.STATUS_IN_PROGRESS, Order.STATUS_CANCELLED}
    ),
    Order.STATUS_IN_PROGRESS: frozenset(
        {Order.STATUS_COMPLETED, Order.STATUS_CANCELLED}
    ),
    Order.STATUS_COMPLETED: frozenset(),
    Order.STATUS_CANCELLED: frozenset(),
}


def allowed_targets(current_status: str) -> frozenset[str]:
    return ALLOWED_TRANSITIONS.get(current_status, frozenset())


@transaction.atomic
def transition_order_status(
    order: Order,
    new_status: str,
    *,
    reason: str = "",
    allow_paid_cancel: bool = False,
    allow_system_override: bool = False,
) -> Order:
    """
    Идемпотентно: если статус уже new_status — вернуть без side-effects.
    Cancel → cancel_order_and_release_stock (резерв + 1С).
    allow_system_override: только для явных системных сценариев
    (например LATE_ONLINE_PAYMENT_POLICY=revive), не для Admin/API.
    """
    locked = Order.objects.select_for_update().get(pk=order.pk)
    current = locked.status

    if new_status == current:
        return locked

    if new_status not in allowed_targets(current) and not allow_system_override:
        raise OrderTransitionError(
            f"Недопустимый переход статуса: {current} → {new_status}",
            code="invalid_transition",
        )

    if new_status == Order.STATUS_CANCELLED:
        from apps.orders.services import cancel_order_and_release_stock

        return cancel_order_and_release_stock(
            locked,
            reason=reason or "status_transition_cancel",
            allow_paid=allow_paid_cancel,
        )

    locked.status = new_status
    locked.save(update_fields=["status", "updated_at"])
    logger.info(
        "Order %s status %s → %s%s",
        locked.order_number,
        current,
        new_status,
        f" ({reason})" if reason else "",
    )
    return locked
