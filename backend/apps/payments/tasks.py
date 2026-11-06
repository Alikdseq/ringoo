"""Celery-задачи платежей."""

from __future__ import annotations

import logging

from config.optional_task import shared_task

logger = logging.getLogger(__name__)


@shared_task
def expire_unpaid_online_orders_task():
    """
    Периодическая отмена неоплаченных online-заказов и снятие резерва.
    INT-007: distributed lock — один активный проход.
    """
    from .locks import EXPIRE_LOCK_KEY, expire_lock_ttl, task_lock
    from .services import expire_unpaid_online_orders

    with task_lock(EXPIRE_LOCK_KEY, ttl_seconds=expire_lock_ttl()) as acquired:
        if not acquired:
            result = {"skipped": True, "reason": "lock_held"}
            logger.info("expire_unpaid_online_orders: %s", result)
            return result
        result = expire_unpaid_online_orders()
        logger.info("expire_unpaid_online_orders: %s", result)
        return result


@shared_task
def reconcile_open_payments_task():
    """Сверка зависших платежей с банком (пропущенный callback). INT-007 lock."""
    from .locks import RECONCILE_LOCK_KEY, reconcile_lock_ttl, task_lock
    from .services import reconcile_open_payments

    with task_lock(RECONCILE_LOCK_KEY, ttl_seconds=reconcile_lock_ttl()) as acquired:
        if not acquired:
            result = {"skipped": True, "reason": "lock_held"}
            logger.info("reconcile_open_payments: %s", result)
            return result
        result = reconcile_open_payments(older_than_minutes=2, limit=100)
        logger.info("reconcile_open_payments: %s", result)
        return result
