"""
Подтверждённая карта складов 1С → Ringoo (BLOCK 2).

Сопоставление в runtime — только по warehouseId (onec_warehouse_id).
Автосоздание Store при импорте запрещено.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ConfirmedWarehouse:
    warehouse_id: str
    onec_name: str
    ringoo_label: str
    is_warehouse: bool
    # Подсказка для ops-маппинга (list_onec_warehouses); не используется как ключ импорта.
    suggested_slug: str


# Все 9 соответствий подтверждены заказчиком.
CONFIRMED_WAREHOUSES: tuple[ConfirmedWarehouse, ...] = (
    ConfirmedWarehouse(
        warehouse_id="7d0745da-cea9-11f0-82e3-00155d01c802",
        onec_name="Ардон",
        ringoo_label="Ардон, Советов, 1",
        is_warehouse=False,
        suggested_slug="ardon-sovetov-1",
    ),
    ConfirmedWarehouse(
        warehouse_id="1418e927-cea5-11f0-82e3-00155d01c802",
        onec_name="БАМ",
        ringoo_label="Владикавказская, 35",
        is_warehouse=False,
        suggested_slug="vladikavkazskaya-35",
    ),
    ConfirmedWarehouse(
        warehouse_id="8d9cc921-cea9-11f0-82e3-00155d01c802",
        onec_name="Беслан",
        ringoo_label="Беслан, Сигова, 52",
        is_warehouse=False,
        suggested_slug="beslan-sigova-52",
    ),
    ConfirmedWarehouse(
        warehouse_id="9de5e8ce-cea9-11f0-82e3-00155d01c802",
        onec_name="Ватутина",
        ringoo_label="Ватутина, 33",
        is_warehouse=False,
        suggested_slug="vatutina-33",
    ),
    ConfirmedWarehouse(
        warehouse_id="710472c0-866e-11f0-82e1-00155d01c802",
        onec_name="Доватора",
        ringoo_label="Доватора, 5",
        is_warehouse=False,
        suggested_slug="dovatora-5",
    ),
    ConfirmedWarehouse(
        warehouse_id="ae0d8ae3-cea9-11f0-82e3-00155d01c802",
        onec_name="Кирова",
        ringoo_label="Кирова, 41",
        is_warehouse=False,
        suggested_slug="kirova-41",
    ),
    ConfirmedWarehouse(
        warehouse_id="bd718455-cea9-11f0-82e3-00155d01c802",
        onec_name="Коста 199",
        ringoo_label="Коста, 199",
        is_warehouse=False,
        suggested_slug="kosta-199",
    ),
    ConfirmedWarehouse(
        warehouse_id="cedfb76d-cea9-11f0-82e3-00155d01c802",
        onec_name="Коста 288",
        ringoo_label="Коста, 288",
        is_warehouse=False,
        suggested_slug="kosta-288",
    ),
    ConfirmedWarehouse(
        warehouse_id="63f7e17d-cea9-11f0-82e3-00155d01c802",
        onec_name="Склад",
        ringoo_label="Склад",
        is_warehouse=True,  # метка для клиентов; точка участвует в наличии/заказе
        suggested_slug="tech-sklad",
    ),
)

CONFIRMED_WAREHOUSE_IDS: frozenset[str] = frozenset(w.warehouse_id for w in CONFIRMED_WAREHOUSES)

CONFIRMED_BY_ID: dict[str, ConfirmedWarehouse] = {w.warehouse_id: w for w in CONFIRMED_WAREHOUSES}


def is_confirmed_warehouse_id(warehouse_id: str | None) -> bool:
    wid = (warehouse_id or "").strip()
    return bool(wid) and wid in CONFIRMED_WAREHOUSE_IDS


def mapping_rows_for_ops() -> list[dict]:
    """JSON-совместимые строки для manage.py list_onec_warehouses --apply."""
    return [
        {
            "slug": w.suggested_slug,
            "onec_warehouse_id": w.warehouse_id,
            "onec_warehouse_name": w.onec_name,
            "is_warehouse": w.is_warehouse,
            "ringoo_label": w.ringoo_label,
        }
        for w in CONFIRMED_WAREHOUSES
    ]


def unknown_ids(warehouse_ids: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in warehouse_ids:
        wid = (raw or "").strip()
        if not wid or wid in seen:
            continue
        seen.add(wid)
        if wid not in CONFIRMED_WAREHOUSE_IDS:
            out.append(wid)
    return out
