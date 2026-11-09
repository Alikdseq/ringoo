"""Сервисные операции над заказами (отмена, резерв, обезличивание)."""

from __future__ import annotations

import logging

from django.db import transaction

from apps.orders.models import Order

logger = logging.getLogger(__name__)


class OrderCancelError(Exception):
    """Бизнес-отказ в отмене заказа (FUNC-002 / FUNC-009)."""

    def __init__(self, message: str, *, code: str = "cancel_denied"):
        self.message = message
        self.code = code
        super().__init__(message)


def order_has_successful_payment(order: Order) -> bool:
    """
    Успешная/блокирующая онлайн-оплата: отмена без refund flow запрещена.
    Наличные / карта при получении не создают Payment.STATUS_PAID.
    """
    from apps.payments.models import Payment

    return order.payments.filter(
        status__in=(
            Payment.STATUS_PAID,
            Payment.STATUS_NEEDS_REVIEW,
        )
    ).exists()


def customer_may_cancel_order(order: Order) -> bool:
    """Статусы + отсутствие успешной оплаты."""
    from apps.orders.services.transitions import normalize_status

    if normalize_status(order.status) not in (
        Order.STATUS_NEW,
        Order.STATUS_PROCESSING,
    ):
        return False
    if order.is_cancelled():
        return False
    if order_has_successful_payment(order):
        return False
    if order.payment_status == Order.PAYMENT_STATUS_PAID:
        return False
    return True


@transaction.atomic
def cancel_order_and_release_stock(
    order: Order,
    *,
    reason: str = "",
    allow_paid: bool = False,
    skip_onec_cancel: bool = False,
) -> Order:
    """
    Единый путь отмены заказа (FUNC-002 / SEC-003):
    status=closed + result=cancelled → release резерва → enqueue 1С cancel.

    Идемпотентно для уже отменённых.
    skip_onec_cancel: отмена пришла из 1С — не слать SiteOrders/cancel обратно.
    """
    locked = (
        Order.objects.select_for_update()
        .prefetch_related("items", "payments")
        .get(pk=order.pk)
    )
    was_active = not locked.is_cancelled()

    if was_active and not allow_paid and (
        order_has_successful_payment(locked)
        or locked.payment_status == Order.PAYMENT_STATUS_PAID
    ):
        raise OrderCancelError(
            "Заказ уже оплачен. Для отмены и возврата обратитесь в поддержку.",
            code="paid_order_cancel_forbidden",
        )

    if was_active:
        locked.status = Order.STATUS_CLOSED
        locked.closure_result = Order.CLOSURE_CANCELLED
        locked.save(update_fields=["status", "closure_result", "updated_at"])
        logger.info(
            "Order %s cancelled%s",
            locked.order_number,
            f" ({reason})" if reason else "",
        )

        from integrations.onec.orders import release_order_item_reservations

        release_order_item_reservations(locked)

        if not skip_onec_cancel:
            order_pk = locked.pk

            def _enqueue_onec_cancel():
                from apps.orders.tasks import enqueue_order_cancel

                enqueue_order_cancel(order_pk)

            transaction.on_commit(_enqueue_onec_cancel)

    return locked
