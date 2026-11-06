"""
Обёртки Stock-операций с обязательным StockMovement (INT-009 complete).

Все изменения reserved_quantity / quantity для бизнес-операций должны
проходить через эти функции либо через record_stock_movement напрямую
(admin / 1С reconciliation).
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.stores.ledger import record_stock_movement
from apps.stores.models import Stock, StockMovement


def _sum_reserved(product_id, store_id=None, series_id: str | None = None) -> int:
    qs = Stock.objects.filter(product_id=product_id)
    if store_id is not None:
        qs = qs.filter(store_id=store_id)
    if series_id is not None:
        qs = qs.filter(onec_series_id=(series_id or "").strip())
    return sum(int(r.reserved_quantity) for r in qs)


def _sum_qty(product_id, store_id=None, series_id: str | None = None) -> int:
    qs = Stock.objects.filter(product_id=product_id)
    if store_id is not None:
        qs = qs.filter(store_id=store_id)
    if series_id is not None:
        qs = qs.filter(onec_series_id=(series_id or "").strip())
    return sum(int(r.quantity) for r in qs)


def _auto_key(prefix: str) -> str:
    return f"{prefix}:{uuid.uuid4().hex}"[:128]


@transaction.atomic
def reserve_at_store(
    product_id,
    store_id,
    amount: int,
    *,
    series_id: str = "",
    idempotency_key: str | None = None,
    order_id=None,
    order_item_id=None,
    reason: str = "",
    source: str = "stock_ops.reserve_at_store",
) -> bool:
    key = (idempotency_key or _auto_key("reserve"))[:128]
    if StockMovement.objects.filter(idempotency_key=key, success=True).exists():
        return True
    series = (series_id or "").strip()
    before = _sum_reserved(product_id, store_id, series if series else "")
    if series:
        # for non-series sum use all blank series rows via reserve_atomic
        before = _sum_reserved(product_id, store_id, series)
        ok = Stock.reserve_series_atomic(product_id, store_id, series, amount)
    else:
        before = _sum_reserved(product_id, store_id, "")
        ok = Stock.reserve_atomic(product_id, store_id, amount)
    after = _sum_reserved(
        product_id, store_id, series if series else ""
    )
    record_stock_movement(
        operation=StockMovement.OP_RESERVE,
        idempotency_key=key,
        quantity=int(amount),
        product_id=product_id,
        store_id=store_id,
        order_id=order_id,
        order_item_id=order_item_id,
        reserved_before=before,
        reserved_after=after if ok else before,
        onec_series_id=series,
        reason=reason,
        source=source,
        success=bool(ok),
        error_message="" if ok else "insufficient_stock",
    )
    return bool(ok)


@transaction.atomic
def release_at_store(
    product_id,
    store_id,
    amount: int,
    *,
    series_id: str = "",
    idempotency_key: str | None = None,
    order_id=None,
    order_item_id=None,
    reason: str = "",
    source: str = "stock_ops.release_at_store",
) -> bool:
    key = (idempotency_key or _auto_key("release"))[:128]
    if StockMovement.objects.filter(idempotency_key=key, success=True).exists():
        return True
    series = (series_id or "").strip()
    before = _sum_reserved(product_id, store_id, series if series else "")
    if series:
        ok = Stock.release_series_atomic(product_id, store_id, series, amount)
    else:
        ok = Stock.release_at_store(product_id, store_id, amount)
    after = _sum_reserved(product_id, store_id, series if series else "")
    record_stock_movement(
        operation=StockMovement.OP_RELEASE,
        idempotency_key=key,
        quantity=int(amount),
        product_id=product_id,
        store_id=store_id,
        order_id=order_id,
        order_item_id=order_item_id,
        reserved_before=before,
        reserved_after=after if ok else before,
        onec_series_id=series,
        reason=reason,
        source=source,
        success=bool(ok),
        error_message="" if ok else "release_incomplete",
    )
    return bool(ok)


@transaction.atomic
def reserve_for_delivery(
    product_id,
    amount: int,
    *,
    idempotency_key: str | None = None,
    order_id=None,
    reason: str = "",
    source: str = "stock_ops.reserve_for_delivery",
) -> bool:
    key = (idempotency_key or _auto_key("reserve_net"))[:128]
    if StockMovement.objects.filter(idempotency_key=key, success=True).exists():
        return True
    before = _sum_reserved(product_id)
    ok = Stock.reserve_for_delivery(product_id, amount)
    after = _sum_reserved(product_id)
    record_stock_movement(
        operation=StockMovement.OP_RESERVE,
        idempotency_key=key,
        quantity=int(amount),
        product_id=product_id,
        store_id=None,
        order_id=order_id,
        reserved_before=before,
        reserved_after=after if ok else before,
        reason=reason or "delivery_network_reserve",
        source=source,
        success=bool(ok),
        error_message="" if ok else "insufficient_stock",
    )
    return bool(ok)


@transaction.atomic
def release_for_delivery(
    product_id,
    amount: int,
    *,
    idempotency_key: str | None = None,
    order_id=None,
    reason: str = "",
    source: str = "stock_ops.release_for_delivery",
) -> bool:
    key = (idempotency_key or _auto_key("release_net"))[:128]
    if StockMovement.objects.filter(idempotency_key=key, success=True).exists():
        return True
    before = _sum_reserved(product_id)
    ok = Stock.release_for_delivery(product_id, amount)
    after = _sum_reserved(product_id)
    record_stock_movement(
        operation=StockMovement.OP_RELEASE,
        idempotency_key=key,
        quantity=int(amount),
        product_id=product_id,
        store_id=None,
        order_id=order_id,
        reserved_before=before,
        reserved_after=after if ok else before,
        reason=reason or "delivery_network_release",
        source=source,
        success=bool(ok),
        error_message="" if ok else "release_incomplete",
    )
    return bool(ok)


@transaction.atomic
def apply_quantity_correction(
    stock: Stock,
    *,
    new_quantity: int | None = None,
    new_reserved: int | None = None,
    idempotency_key: str | None = None,
    reason: str = "admin_correction",
    source: str = "admin_api.stock",
) -> Stock:
    """Ручная правка quantity/reserved администратором."""
    key = (idempotency_key or _auto_key(f"corr:{stock.pk}"))[:128]
    if StockMovement.objects.filter(idempotency_key=key, success=True).exists():
        return Stock.objects.get(pk=stock.pk)

    locked = Stock.objects.select_for_update().get(pk=stock.pk)
    qty_before = int(locked.quantity)
    res_before = int(locked.reserved_quantity)
    if new_quantity is not None:
        locked.quantity = max(0, int(new_quantity))
    if new_reserved is not None:
        locked.reserved_quantity = max(0, int(new_reserved))
    if locked.reserved_quantity > locked.quantity:
        raise ValueError("reserved_quantity cannot exceed quantity")
    locked.updated_at = timezone.now()
    locked.save(update_fields=["quantity", "reserved_quantity", "updated_at"])
    record_stock_movement(
        operation=StockMovement.OP_CORRECTION,
        idempotency_key=key,
        quantity=abs(int(locked.quantity) - qty_before),
        product_id=locked.product_id,
        store_id=locked.store_id,
        reserved_before=res_before,
        reserved_after=int(locked.reserved_quantity),
        stock_quantity_before=qty_before,
        stock_quantity_after=int(locked.quantity),
        onec_series_id=locked.onec_series_id or "",
        reason=reason,
        source=source,
        success=True,
    )
    return locked


@transaction.atomic
def apply_onec_stock_upsert(
    *,
    product_id,
    store_id,
    series_id: str,
    series_name: str,
    quantity: int,
    idempotency_key: str | None = None,
    source: str = "onec.importer",
) -> tuple[Any, bool]:
    """Импорт остатка из 1С → reconciliation в журнале."""
    series_id = (series_id or "").strip()
    key = (
        idempotency_key
        or f"onec_stock:{product_id}:{store_id}:{series_id}:{quantity}"
    )[:128]
    if StockMovement.objects.filter(idempotency_key=key, success=True).exists():
        row = Stock.objects.filter(
            product_id=product_id, store_id=store_id, onec_series_id=series_id
        ).first()
        return row, False

    existing = Stock.objects.filter(
        product_id=product_id, store_id=store_id, onec_series_id=series_id
    ).first()
    qty_before = int(existing.quantity) if existing else 0
    res_before = int(existing.reserved_quantity) if existing else 0
    row, created = Stock.objects.update_or_create(
        product_id=product_id,
        store_id=store_id,
        onec_series_id=series_id,
        defaults={
            "quantity": max(0, int(quantity)),
            "onec_series_name": (series_name or "")[:255],
        },
    )
    # Не затираем reserved при upsert quantity-only (defaults не трогают reserved)
    row.refresh_from_db()
    record_stock_movement(
        operation=StockMovement.OP_RECONCILIATION,
        idempotency_key=key,
        quantity=abs(int(row.quantity) - qty_before),
        product_id=product_id,
        store_id=store_id,
        reserved_before=res_before,
        reserved_after=int(row.reserved_quantity),
        stock_quantity_before=qty_before,
        stock_quantity_after=int(row.quantity),
        onec_series_id=series_id,
        reason="onec_stock_upsert",
        source=source,
        success=True,
    )
    return row, created
