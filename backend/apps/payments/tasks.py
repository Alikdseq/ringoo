"""Celery-задачи платежей."""

from __future__ import annotations

import logging

from config.optional_task import shared_task

logger = logging.getLogger(__name__)


@shared_task
def expire_unpaid_online_orders_task():
    """Периодическая отмена неоплаченных online-заказов и снятие резерва."""
    from .services import expire_unpaid_online_orders

    result = expire_unpaid_online_orders()
    logger.info("expire_unpaid_online_orders: %s", result)
    return result


@shared_task
def reconcile_open_payments_task():
    """Сверка зависших платежей с банком (пропущенный callback)."""
    from .services import reconcile_open_payments

    result = reconcile_open_payments(older_than_minutes=2, limit=100)
    logger.info("reconcile_open_payments: %s", result)
    return result
