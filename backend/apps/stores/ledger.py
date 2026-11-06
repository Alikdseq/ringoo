"""
Запись StockMovement в той же транзакции, что и изменение Stock (INT-009).
Идемпотентность через unique idempotency_key.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)


def record_stock_movement(
    *,
    operation: str,
    idempotency_key: str,
    quantity: int,
    product_id=None,
    store_id=None,
    order_id=None,
    order_item_id=None,
    reserved_before: int = 0,
    reserved_after: int = 0,
    stock_quantity_before: int | None = None,
    stock_quantity_after: int | None = None,
    onec_series_id: str = "",
    reason: str = "",
    source: str = "",
    success: bool = True,
    error_message: str = "",
) -> Any | None:
    from apps.stores.models import StockMovement

    key = (idempotency_key or "")[:128]
    if not key:
        raise ValueError("idempotency_key required")

    try:
        with transaction.atomic():
            return StockMovement.objects.create(
                operation=operation,
                idempotency_key=key,
                quantity=max(0, int(quantity)),
                product_id=product_id,
                store_id=store_id,
                order_id=order_id,
                order_item_id=order_item_id,
                reserved_before=int(reserved_before),
                reserved_after=int(reserved_after),
                stock_quantity_before=stock_quantity_before,
                stock_quantity_after=stock_quantity_after,
                onec_series_id=(onec_series_id or "")[:64],
                reason=(reason or "")[:255],
                source=(source or "")[:64],
                success=bool(success),
                error_message=(error_message or "")[:512],
            )
    except IntegrityError:
        # Повтор той же бизнес-операции — не дублируем журнал
        existing = StockMovement.objects.filter(idempotency_key=key).first()
        logger.info("stock_movement idempotent hit key=%s", key)
        return existing
