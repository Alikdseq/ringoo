"""
BLOCK 2: привязка подтверждённых warehouseId 1С к существующим Store.

- 8 розничных точек: обновляем onec_warehouse_id / name / is_warehouse
  по slug (ID Store и адреса не меняем).
- Точка «Склад»/Apple Room: создаём только если нет (slug=tech-sklad),
  is_warehouse=True (метка для клиентов), is_active=True (участвует в наличии/заказе).
- Не удаляет и не пересоздаёт существующие магазины.
"""

from django.db import migrations


# warehouse_id, onec_name, slug, is_warehouse, create_if_missing, ringoo_label
CONFIRMED = (
    (
        "7d0745da-cea9-11f0-82e3-00155d01c802",
        "Ардон",
        "ardon-sovetov-1",
        False,
        False,
        "Ардон, Советов, 1",
    ),
    (
        "1418e927-cea5-11f0-82e3-00155d01c802",
        "БАМ",
        "vladikavkazskaya-35",
        False,
        False,
        "Владикавказская, 35",
    ),
    (
        "8d9cc921-cea9-11f0-82e3-00155d01c802",
        "Беслан",
        "beslan-sigova-52",
        False,
        False,
        "Беслан, Сигова, 52",
    ),
    (
        "9de5e8ce-cea9-11f0-82e3-00155d01c802",
        "Ватутина",
        "vatutina-33",
        False,
        False,
        "Ватутина, 33",
    ),
    (
        "710472c0-866e-11f0-82e1-00155d01c802",
        "Доватора",
        "dovatora-5",
        False,
        False,
        "Доватора, 5",
    ),
    (
        "ae0d8ae3-cea9-11f0-82e3-00155d01c802",
        "Кирова",
        "kirova-41",
        False,
        False,
        "Кирова, 41",
    ),
    (
        "bd718455-cea9-11f0-82e3-00155d01c802",
        "Коста 199",
        "kosta-199",
        False,
        False,
        "Коста, 199",
    ),
    (
        "cedfb76d-cea9-11f0-82e3-00155d01c802",
        "Коста 288",
        "kosta-288",
        False,
        False,
        "Коста, 288",
    ),
    (
        "63f7e17d-cea9-11f0-82e3-00155d01c802",
        "Склад",
        "tech-sklad",
        True,
        True,
        "Склад",
    ),
)


def apply_mapping(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    for wid, onec_name, slug, is_wh, create_missing, label in CONFIRMED:
        store = Store.objects.filter(slug=slug).first()
        if store is None and create_missing:
            Store.objects.create(
                slug=slug,
                name=label,
                address=label,
                city="Владикавказ",
                onec_warehouse_id=wid,
                onec_warehouse_name=onec_name,
                is_warehouse=True,
                is_active=True,
            )
            continue
        if store is None:
            # Розничный slug отсутствует — не создаём дубль; ops должен
            # завести точку вручную и прогнать list_onec_warehouses --apply.
            continue
        dirty = []
        if store.onec_warehouse_id != wid:
            store.onec_warehouse_id = wid
            dirty.append("onec_warehouse_id")
        if store.onec_warehouse_name != onec_name:
            store.onec_warehouse_name = onec_name
            dirty.append("onec_warehouse_name")
        if store.is_warehouse != is_wh:
            store.is_warehouse = is_wh
            dirty.append("is_warehouse")
        if is_wh and not store.is_active:
            # Склад/Apple Room — активная точка продажи с меткой «склад».
            store.is_active = True
            dirty.append("is_active")
        if dirty:
            store.save(update_fields=dirty + ["updated_at"])


def reverse_mapping(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    for wid, _onec_name, slug, is_wh, create_missing, _label in CONFIRMED:
        store = Store.objects.filter(slug=slug).first()
        if store is None:
            continue
        if create_missing and is_wh:
            # Удаляем только техсклад, созданный этой миграцией.
            Store.objects.filter(slug=slug, onec_warehouse_id=wid).delete()
            continue
        store.onec_warehouse_id = None
        store.onec_warehouse_name = None
        store.is_warehouse = False
        store.save(
            update_fields=[
                "onec_warehouse_id",
                "onec_warehouse_name",
                "is_warehouse",
                "updated_at",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0007_stockmovement"),
    ]

    operations = [
        migrations.RunPython(apply_mapping, reverse_mapping),
    ]
