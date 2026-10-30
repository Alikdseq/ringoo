"""
Celery-задачи заказов: уведомления и синхронизация с 1С.
"""

import logging

from django.utils import timezone

from config.optional_task import is_celery_available, shared_task

logger = logging.getLogger(__name__)


@shared_task
def sync_order_to_onec_task(order_id, paid=False, _attempt=0):
    """Асинхронная отправка заказа в 1С (не блокирует оформление на сайте)."""
    from django.conf import settings

    from integrations.onec.orders import OneCOrderSyncError, sync_order_to_onec

    try:
        return sync_order_to_onec(order_id, paid=bool(paid))
    except OneCOrderSyncError as exc:
        max_attempts = int(getattr(settings, "ONE_C_ORDER_SYNC_MAX_ATTEMPTS", 5))
        attempt = int(_attempt or 0)
        if (
            exc.retryable
            and attempt + 1 < max_attempts
            and is_celery_available()
        ):
            countdown = min(60 * (2**attempt), 600)
            logger.warning(
                "1C sync retry order=%s paid=%s attempt=%s countdown=%s: %s",
                order_id,
                paid,
                attempt + 1,
                countdown,
                exc,
            )
            return sync_order_to_onec_task.apply_async(
                args=(order_id,),
                kwargs={"paid": bool(paid), "_attempt": attempt + 1},
                countdown=countdown,
            )
        if exc.retryable and not is_celery_available():
            logger.error(
                "1C sync failed order=%s (stub: no recursive retry): %s",
                order_id,
                exc,
            )
        else:
            logger.error("1C sync failed order=%s paid=%s: %s", order_id, paid, exc)
        return {
            "ok": False,
            "order_id": str(order_id),
            "error": str(exc),
            "retryable": exc.retryable,
        }


@shared_task
def cancel_order_in_onec_task(order_id, _attempt=0):
    from django.conf import settings

    from integrations.onec.orders import OneCOrderSyncError, cancel_order_in_onec

    try:
        return cancel_order_in_onec(order_id)
    except OneCOrderSyncError as exc:
        max_attempts = int(getattr(settings, "ONE_C_ORDER_SYNC_MAX_ATTEMPTS", 5))
        attempt = int(_attempt or 0)
        if (
            exc.retryable
            and attempt + 1 < max_attempts
            and is_celery_available()
        ):
            countdown = min(60 * (2**attempt), 600)
            logger.warning(
                "1C cancel retry order=%s attempt=%s countdown=%s: %s",
                order_id,
                attempt + 1,
                countdown,
                exc,
            )
            return cancel_order_in_onec_task.apply_async(
                args=(order_id,),
                kwargs={"_attempt": attempt + 1},
                countdown=countdown,
            )
        logger.error("1C cancel failed order=%s: %s", order_id, exc)
        return {
            "ok": False,
            "order_id": str(order_id),
            "error": str(exc),
            "retryable": exc.retryable,
        }


def enqueue_order_sync(order_id, *, paid: bool = False) -> None:
    try:
        sync_order_to_onec_task.delay(str(order_id), paid=bool(paid))
    except Exception:
        logger.exception("Failed to enqueue 1C sync for order=%s", order_id)


def enqueue_order_cancel(order_id) -> None:
    try:
        cancel_order_in_onec_task.delay(str(order_id))
    except Exception:
        logger.exception("Failed to enqueue 1C cancel for order=%s", order_id)


@shared_task
def send_order_notifications(order_id):
    """
    Отправка уведомлений по заказу: email с подтверждением и ссылкой на оценку.

    Идемпотентность: при повторной доставке задачи (retry Celery) письмо не отправляется
    повторно, если уже стоит confirmation_email_sent_at.
    """
    from .models import Order
    from integrations.email_service import send_order_confirmation

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("send_order_notifications: order %s not found", order_id)
        return {"order_id": str(order_id), "sent": False, "reason": "not_found"}

    if order.confirmation_email_sent_at:
        logger.info(
            "send_order_notifications: skip duplicate for order %s (already sent at %s)",
            order.order_number,
            order.confirmation_email_sent_at,
        )
        return {
            "order_id": str(order_id),
            "sent": False,
            "skipped": True,
            "reason": "already_sent",
        }

    sent = send_order_confirmation(order)
    if sent:
        updated = Order.objects.filter(
            pk=order_id,
            confirmation_email_sent_at__isnull=True,
        ).update(confirmation_email_sent_at=timezone.now())
        if not updated:
            logger.warning(
                "send_order_notifications: race marking sent for order %s",
                order.order_number,
            )
    return {"order_id": str(order_id), "sent": bool(sent)}
