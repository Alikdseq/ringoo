"""
Распределённые lock/lease для фоновых платёжных задач (INT-007).

Используется django cache (Redis в prod, LocMem в тестах).
TTL защищает от вечной блокировки при падении worker.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

EXPIRE_LOCK_KEY = "payments:expire_unpaid_online_orders:lock"
RECONCILE_LOCK_KEY = "payments:reconcile_open_payments:lock"


def _ttl(name: str, default: int) -> int:
    return int(getattr(settings, name, default) or default)


@contextmanager
def task_lock(cache_key: str, *, ttl_seconds: int) -> Iterator[bool]:
    """
    Yields True if lock acquired, False if already held.
    Always releases only if this caller acquired the lock.
    """
    acquired = cache.add(cache_key, "1", timeout=max(5, int(ttl_seconds)))
    if not acquired:
        logger.info("task_lock busy key=%s", cache_key)
        yield False
        return
    try:
        yield True
    finally:
        try:
            cache.delete(cache_key)
        except Exception:
            logger.warning("task_lock release failed key=%s", cache_key, exc_info=True)


def expire_lock_ttl() -> int:
    return _ttl("PAYMENTS_EXPIRE_LOCK_TTL_SECONDS", 240)


def reconcile_lock_ttl() -> int:
    return _ttl("PAYMENTS_RECONCILE_LOCK_TTL_SECONDS", 180)
