# Data migration: магазины и менеджеры по списку заказчика

from django.db import migrations


def seed_stores_and_managers(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    Manager = apps.get_model("stores", "Manager")

    # (slug, city, address, display_name для магазина)
    stores_data = [
        ("kosta-288", "Владикавказ", "ул. Коста, 288", "Коста, 288"),
        ("kosta-199", "Владикавказ", "ул. Коста, 199", "Коста, 199"),
        ("kirova-41", "Владикавказ", "ул. Кирова, 41", "Кирова, 41"),
        ("vatutina-33", "Владикавказ", "ул. Ватутина, 33", "Ватутина, 33"),
        ("dovatora-5", "Владикавказ", "ул. Доватора, 5", "Доватора, 5"),
        ("vladikavkazskaya-35", "Владикавказ", "ул. Владикавказская, 35", "Владикавказская, 35"),
        ("beslan-sigova-52", "Беслан", "ул. Сигова, 52", "Беслан, Сигова 52"),
        ("ardon-sovetov-1", "Ардон", "ул. Советов, 1", "Ардон, Советов 1"),
    ]

    # Менеджеры по магазинам: slug магазина -> список ФИО
    managers_by_store = {
        "kosta-288": ["Гогаев Сослан", "Джалилов Джалилбек", "Бедоева Алина"],
        "kosta-199": ["Кундухова Елизавета", "Водянкина Александра", "Елоева Марина"],
        "kirova-41": ["Валиева Илона", "Маргиев Тамерлан"],
        "vatutina-33": [
            "Дзгоева Яна",
            "Калуева Алина",
            "Авакян Элина",
            "Рамонова Виктория",
        ],
        "dovatora-5": ["Казорина Ирина", "Донских Елена"],
        "vladikavkazskaya-35": ["Гадоева Яна", "Гагиев Хасан", "Хугаев Азамат"],
        "beslan-sigova-52": ["Гадзаова Лариса", "Бутаева Данна", "Дзебисова Анна"],
        "ardon-sovetov-1": ["Гутнова Залина", "Сотиева Алина", "Бекузаров Алихан"],
    }

    for slug, city, address, display_name in stores_data:
        store, _ = Store.objects.get_or_create(
            slug=slug,
            defaults={
                "name": display_name,
                "address": address,
                "city": city,
                "is_active": True,
            },
        )
        for order, name in enumerate(managers_by_store.get(slug, [])):
            Manager.objects.get_or_create(
                store=store,
                name=name,
                defaults={"is_active": True, "order": order},
            )


def reverse_seed(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    slugs = [
        "kosta-288", "kosta-199", "kirova-41", "vatutina-33",
        "dovatora-5", "vladikavkazskaya-35", "beslan-sigova-52", "ardon-sovetov-1",
    ]
    Manager.objects.filter(store__slug__in=slugs).delete()
    Store.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0002_add_manager_model"),
    ]

    operations = [
        migrations.RunPython(seed_stores_and_managers, reverse_seed),
    ]
