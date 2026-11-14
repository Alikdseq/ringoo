"""Общие хелперы для тестов импорта 1С (подтверждённые склады)."""

from __future__ import annotations

from apps.stores.models import Store
from integrations.onec.warehouse_map import CONFIRMED_WAREHOUSES


def ensure_confirmed_stores() -> dict[str, Store]:
    """
    Гарантирует 9 подтверждённых складов без дублей.
    Сначала ищет по slug (как seed/миграция), затем по warehouseId.
    """
    by_id: dict[str, Store] = {}
    for w in CONFIRMED_WAREHOUSES:
        store = (
            Store.objects.filter(slug=w.suggested_slug).first()
            or Store.objects.filter(onec_warehouse_id=w.warehouse_id).first()
        )
        if store is None:
            store = Store.objects.create(
                name=w.ringoo_label,
                slug=w.suggested_slug,
                address=w.ringoo_label,
                city="Тест",
                onec_warehouse_id=w.warehouse_id,
                onec_warehouse_name=w.onec_name,
                is_warehouse=w.is_warehouse,
                is_active=True,
            )
        else:
            dirty = []
            if store.onec_warehouse_id != w.warehouse_id:
                store.onec_warehouse_id = w.warehouse_id
                dirty.append("onec_warehouse_id")
            if store.onec_warehouse_name != w.onec_name:
                store.onec_warehouse_name = w.onec_name
                dirty.append("onec_warehouse_name")
            if store.is_warehouse != w.is_warehouse:
                store.is_warehouse = w.is_warehouse
                dirty.append("is_warehouse")
            if not store.is_active:
                store.is_active = True
                dirty.append("is_active")
            if dirty:
                store.save(update_fields=[*dirty, "updated_at"])
        by_id[w.warehouse_id] = store
    return by_id


# Удобный warehouseId для «основного» розничного магазина в тестах (БАМ).
TEST_RETAIL_WH_ID = "1418e927-cea5-11f0-82e3-00155d01c802"
TEST_RETAIL_WH_NAME = "БАМ"
TEST_OTHER_WH_ID = "8d9cc921-cea9-11f0-82e3-00155d01c802"  # Беслан
TEST_TECH_WH_ID = "63f7e17d-cea9-11f0-82e3-00155d01c802"
