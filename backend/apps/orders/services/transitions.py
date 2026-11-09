"""
Единый FSM переходов статуса заказа (fulfillment).

Статус оплаты (Order.payment_status / Payment) — отдельно; не смешивать.
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


ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    Order.STATUS_NEW: frozenset({Order.STATUS_PROCESSING, Order.STATUS_CLOSED}),
    Order.STATUS_PROCESSING: frozenset({Order.STATUS_READY, Order.STATUS_CLOSED}),
    Order.STATUS_READY: frozenset({Order.STATUS_CLOSED}),
    Order.STATUS_CLOSED: frozenset(),
}


def normalize_status(status: str) -> str:
    """Legacy DB/API codes → текущий FSM."""
    if status in ("confirmed", "in_progress"):
        return Order.STATUS_PROCESSING
    if status in ("completed", "cancelled"):
        return Order.STATUS_CLOSED
    return status


def allowed_targets(current_status: str) -> frozenset[str]:
    return ALLOWED_TRANSITIONS.get(normalize_status(current_status), frozenset())


def _normalize_target(
    new_status: str, closure_result: str | None
) -> tuple[str, str | None]:
    if new_status in ("confirmed", "in_progress"):
        return Order.STATUS_PROCESSING, None
    if new_status == "completed":
        return Order.STATUS_CLOSED, closure_result or Order.CLOSURE_COMPLETED
    if new_status == "cancelled":
        return Order.STATUS_CLOSED, Order.CLOSURE_CANCELLED
    return new_status, closure_result


@transaction.atomic
def transition_order_status(
    order: Order,
    new_status: str,
    *,
    reason: str = "",
    closure_result: str | None = None,
    allow_paid_cancel: bool = False,
    allow_system_override: bool = False,
    skip_onec_cancel: bool = False,
) -> Order:
    """
    Идемпотентно при том же целевом состоянии.
    closed+cancelled → cancel_order_and_release_stock.
    skip_onec_cancel=True — отмена пришла из 1С (не слать cancel обратно).
    """
    new_status, closure_result = _normalize_target(new_status, closure_result)

    locked = Order.objects.select_for_update().get(pk=order.pk)
    current_raw = locked.status
    current = normalize_status(current_raw)

    if new_status == Order.STATUS_CLOSED:
        if closure_result not in (
            Order.CLOSURE_COMPLETED,
            Order.CLOSURE_CANCELLED,
        ):
            raise OrderTransitionError(
                "Для status=closed обязателен result (completed|cancelled)",
                code="closure_result_required",
            )

    # Идемпотентность
    same_closed = (
        new_status == Order.STATUS_CLOSED
        and normalize_status(locked.status) == Order.STATUS_CLOSED
        and (
            locked.closure_result == closure_result
            or (
                locked.status == "cancelled"
                and closure_result == Order.CLOSURE_CANCELLED
            )
            or (
                locked.status == "completed"
                and closure_result == Order.CLOSURE_COMPLETED
            )
        )
    )
    same_open = (
        new_status != Order.STATUS_CLOSED
        and normalize_status(locked.status) == new_status
    )
    if same_closed or same_open:
        # Подтянуть legacy-код в новый при совпадении смысла
        if locked.status != new_status or (
            new_status == Order.STATUS_CLOSED
            and locked.closure_result != closure_result
        ):
            locked.status = new_status
            locked.closure_result = (
                closure_result if new_status == Order.STATUS_CLOSED else None
            )
            locked.save(update_fields=["status", "closure_result", "updated_at"])
        return locked

    if current == Order.STATUS_CLOSED and not allow_system_override:
        raise OrderTransitionError(
            f"Заказ уже завершён ({locked.display_status_code()})",
            code="order_closed",
        )

    if new_status not in allowed_targets(current_raw) and not allow_system_override:
        raise OrderTransitionError(
            f"Недопустимый переход статуса: {current_raw} → {new_status}",
            code="invalid_transition",
        )

    if allow_system_override and current == Order.STATUS_CLOSED and new_status != Order.STATUS_CLOSED:
        # Revive: снимаем результат закрытия
        locked.closure_result = None

    if new_status == Order.STATUS_CLOSED and closure_result == Order.CLOSURE_CANCELLED:
        from apps.orders.services import cancel_order_and_release_stock

        return cancel_order_and_release_stock(
            locked,
            reason=reason or "status_transition_cancel",
            allow_paid=allow_paid_cancel,
            skip_onec_cancel=skip_onec_cancel,
        )

    locked.status = new_status
    update_fields = ["status", "updated_at"]
    if new_status == Order.STATUS_CLOSED:
        locked.closure_result = closure_result
        update_fields.append("closure_result")
    elif locked.closure_result is not None:
        locked.closure_result = None
        update_fields.append("closure_result")

    locked.save(update_fields=update_fields)
    logger.info(
        "Order %s status %s → %s%s%s",
        locked.order_number,
        current_raw,
        new_status,
        f"/{closure_result}" if closure_result else "",
        f" ({reason})" if reason else "",
    )
    return locked
