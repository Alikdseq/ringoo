"""
Celery-задачи заказов: уведомления (F.3 — письмо с ссылкой на оценку).
"""

import logging

from django.utils import timezone

from config.optional_task import shared_task

logger = logging.getLogger(__name__)


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
