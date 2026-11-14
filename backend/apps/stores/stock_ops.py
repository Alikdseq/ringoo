"""
Обёртки Stock-операций с обязательным StockMovement (INT-009 complete).

Все изменения reserved_quantity / quantity для бизнес-операций должны
проходить через эти функции либо через record_stock_movement напрямую
(admin / 1С reconciliation).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from django.db import transaction
from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from apps.stores.ledger import record_stock_movement
from apps.stores.models import Stock, StockMovement

_BATCH_IN_CHUNK = 900

# StockMovement.idempotency_key max_length=128. Prefixed SHA-256 hex is always 69.
_ONEC_IDEMPOTENCY_MAX_LEN = 128


def build_onec_import_idempotency_key(
    run_id: str,
    product_id,
    store_id,
    series_id: str = "",
) -> str:
    """
    Стабильный ключ сверки остатка в рамках одного запуска импорта.

    Не включает quantity: иначе цикл 5→8→5 блокируется историческим :q5.
    Длина всегда фиксирована (onec: + 64 hex = 69) — без обрезки [:128].
    """
    run = (run_id or "").strip()
    if not run:
        raise ValueError("run_id required for onec import idempotency key")
    series = (series_id or "").strip()
    payload = f"{run}:{product_id}:{store_id}:{series}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    key = f"onec:{digest}"
    if len(key) > _ONEC_IDEMPOTENCY_MAX_LEN:
        # Защита от будущих изменений формата; текущий ключ всегда 69.
        raise ValueError(
            f"onec idempotency key length {len(key)} exceeds "
            f"{_ONEC_IDEMPOTENCY_MAX_LEN}"
        )
    return key


def _require_idempotency_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        raise ValueError("idempotency_key required")
    if len(key) > _ONEC_IDEMPOTENCY_MAX_LEN:
        raise ValueError(
            f"idempotency_key length {len(key)} exceeds {_ONEC_IDEMPOTENCY_MAX_LEN}"
        )
    return key


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
def restock_at_store(
    product_id,
    store_id,
    amount: int,
    *,
    series_id: str = "",
    idempotency_key: str | None = None,
    order_id=None,
    order_item_id=None,
    reason: str = "",
    source: str = "stock_ops.restock_at_store",
) -> bool:
    """Увеличение доступного quantity после приёмки возврата (sellable only)."""
    amount = int(amount)
    if amount < 1:
        return False
    key = (idempotency_key or _auto_key("restock"))[:128]
    if StockMovement.objects.filter(idempotency_key=key, success=True).exists():
        return True
    series = (series_id or "").strip()
    qs = Stock.objects.select_for_update().filter(
        product_id=product_id, store_id=store_id, onec_series_id=series
    )
    stock = qs.first()
    qty_before = int(stock.quantity) if stock else 0
    res_before = int(stock.reserved_quantity) if stock else 0
    if stock is None:
        stock = Stock.objects.create(
            product_id=product_id,
            store_id=store_id,
            onec_series_id=series,
            quantity=amount,
            reserved_quantity=0,
        )
    else:
        stock.quantity = int(stock.quantity) + amount
        stock.updated_at = timezone.now()
        stock.save(update_fields=["quantity", "updated_at"])
    record_stock_movement(
        operation=StockMovement.OP_RESTOCK,
        idempotency_key=key,
        quantity=amount,
        product_id=product_id,
        store_id=store_id,
        order_id=order_id,
        order_item_id=order_item_id,
        reserved_before=res_before,
        reserved_after=int(stock.reserved_quantity),
        stock_quantity_before=qty_before,
        stock_quantity_after=int(stock.quantity),
        onec_series_id=series,
        reason=reason,
        source=source,
        success=True,
    )
    return True


@transaction.atomic
def apply_onec_stock_upsert(
    *,
    product_id,
    store_id,
    series_id: str,
    series_name: str,
    quantity: int,
    idempotency_key: str | None = None,
    run_id: str | None = None,
    source: str = "onec.importer",
) -> tuple[Any, bool]:
    """
    Импорт остатка из 1С → reconciliation в журнале.

    Идемпотентность привязана к запуску импорта (run_id / явный ключ), а не к qty.
    reserved_quantity не перезаписывается.
    Возвращает (stock_row, applied): applied=False если успешный ключ уже был.
    """
    series_id = (series_id or "").strip()
    if idempotency_key:
        key = _require_idempotency_key(idempotency_key)
    elif run_id:
        key = build_onec_import_idempotency_key(
            run_id, product_id, store_id, series_id
        )
    else:
        # Прямой вызов без контекста плана: всегда новая операция (не кэшируем по qty).
        key = f"onec_stock:{uuid.uuid4().hex}"
        key = _require_idempotency_key(key)

    # ONEC-024: success=True → идемпотентный skip;
    # success=False с тем же ключом → удаляем failed-запись и повторяем apply.
    prior = StockMovement.objects.filter(idempotency_key=key).first()
    if prior is not None:
        if prior.success:
            row = Stock.objects.filter(
                product_id=product_id, store_id=store_id, onec_series_id=series_id
            ).first()
            return row, False
        prior.delete()

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
    return row, True


@dataclass(frozen=True)
class OnecStockUpsertItem:
    """Одна позиция полного снимка 1С для batch-upsert."""

    product_id: Any
    store_id: Any
    series_id: str
    series_name: str
    quantity: int


def _chunked(seq: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


@transaction.atomic
def apply_onec_stock_upserts_batch(
    items: Sequence[OnecStockUpsertItem],
    *,
    run_id: str,
    source: str = "onec.importer",
) -> dict[str, int]:
    """
    Batch-вариант apply_onec_stock_upsert для полного снимка.

    Сохраняет:
    - idempotency по run_id (ключ без qty);
    - reserved_quantity не перезаписывается;
    - StockMovement на каждую applied-позицию;
    - семантику ONEC-024 (failed prior → retry).

    Не дробит внешнюю транзакцию apply_catalog_import (ONEC-014):
    при вызове из уже atomic-блока создаётся savepoint.
    """
    run = (run_id or "").strip()
    if not run:
        raise ValueError("run_id required for batch onec stock upsert")
    if not items:
        return {"applied": 0, "skipped_idempotent": 0, "unchanged_skipped": 0}

    prepared: list[tuple[str, OnecStockUpsertItem, str, str, int]] = []
    for raw in items:
        series_id = (raw.series_id or "").strip()
        series_name = (raw.series_name or "")[:255]
        qty = max(0, int(raw.quantity))
        key = build_onec_import_idempotency_key(
            run, raw.product_id, raw.store_id, series_id
        )
        prepared.append((key, raw, series_id, series_name, qty))

    keys = [k for k, *_ in prepared]
    prior_by_key: dict[str, StockMovement] = {}
    for chunk in _chunked(keys, _BATCH_IN_CHUNK):
        for mov in StockMovement.objects.filter(idempotency_key__in=list(chunk)):
            prior_by_key[mov.idempotency_key] = mov

    failed_ids = [
        mov.pk
        for mov in prior_by_key.values()
        if not mov.success
    ]
    if failed_ids:
        for chunk in _chunked(failed_ids, _BATCH_IN_CHUNK):
            StockMovement.objects.filter(pk__in=list(chunk)).delete()
        for key, mov in list(prior_by_key.items()):
            if not mov.success:
                prior_by_key.pop(key, None)

    pending_map: dict[str, tuple[str, OnecStockUpsertItem, str, str, int]] = {}
    skipped_idempotent = 0
    for key, raw, series_id, series_name, qty in prepared:
        prior = prior_by_key.get(key)
        if prior is not None and prior.success:
            skipped_idempotent += 1
            continue
        # Один ключ = один product+store+series в run; последний wins.
        pending_map[key] = (key, raw, series_id, series_name, qty)
    pending = list(pending_map.values())

    if not pending:
        return {
            "applied": 0,
            "skipped_idempotent": skipped_idempotent,
            "unchanged_skipped": 0,
        }

    product_ids = {p.product_id for _, p, *_ in pending}
    store_ids = {p.store_id for _, p, *_ in pending}
    existing_map: dict[tuple[str, str, str], Stock] = {}
    for row in Stock.objects.filter(
        product_id__in=product_ids, store_id__in=store_ids
    ).iterator():
        # Нормализуем UUID/str: stocks_to_zero несёт site_* как str из плана.
        existing_map[
            (str(row.product_id), str(row.store_id), row.onec_series_id or "")
        ] = row

    to_create: list[Stock] = []
    to_update: list[Stock] = []
    movements: list[StockMovement] = []
    now = timezone.now()

    for key, raw, series_id, series_name, qty in pending:
        map_key = (str(raw.product_id), str(raw.store_id), series_id)
        existing = existing_map.get(map_key)
        if existing is None:
            qty_before = 0
            res_before = 0
            row = Stock(
                product_id=raw.product_id,
                store_id=raw.store_id,
                onec_series_id=series_id,
                onec_series_name=series_name,
                quantity=qty,
                reserved_quantity=0,
            )
            to_create.append(row)
            existing_map[map_key] = row
            qty_after = qty
            res_after = 0
        else:
            qty_before = int(existing.quantity)
            res_before = int(existing.reserved_quantity)
            existing.quantity = qty
            existing.onec_series_name = series_name
            existing.updated_at = now
            to_update.append(existing)
            qty_after = qty
            res_after = res_before

        movements.append(
            StockMovement(
                operation=StockMovement.OP_RECONCILIATION,
                idempotency_key=key,
                quantity=abs(qty_after - qty_before),
                product_id=raw.product_id,
                store_id=raw.store_id,
                reserved_before=res_before,
                reserved_after=res_after,
                stock_quantity_before=qty_before,
                stock_quantity_after=qty_after,
                onec_series_id=series_id,
                reason="onec_stock_upsert",
                source=source,
                success=True,
            )
        )

    if to_create:
        Stock.objects.bulk_create(to_create, batch_size=500)
    if to_update:
        Stock.objects.bulk_update(
            to_update,
            ["quantity", "onec_series_name", "updated_at"],
            batch_size=500,
        )
    if movements:
        StockMovement.objects.bulk_create(movements, batch_size=500)

    return {
        "applied": len(movements),
        "skipped_idempotent": skipped_idempotent,
        "unchanged_skipped": 0,
    }


def sum_available_quantity(qs) -> int:
    """SQL-сумма max(0, quantity - reserved) без выгрузки строк в Python."""
    result = qs.annotate(
        avail=Greatest(F("quantity") - F("reserved_quantity"), Value(0))
    ).aggregate(total=Coalesce(Sum("avail"), Value(0)))
    return int(result["total"] or 0)
