"""
Настройка главных разделов витрины = флаги на существующих Category 1С.

Не создаёт категории, не меняет parent и Product.category.
Список — точные названия папок из выгрузки 1С (CSV/импорт), не «желаемые» ярлыки витрины.

Matching (configure_catalog_mains), по приоритету:
1) onec_code (уникален в БД);
2) slug (уникален в БД);
3) title — только если ровно одна Category с таким title;
   при 0 или >1 совпадениях узел пропускается (не создаём, не помечаем «все»).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MainSectionSpec:
    """Спека сопоставления желаемого раздела витрины → реальный узел 1С."""

    desired_label: str
    """Ориентир из прежней витрины (только для отчёта)."""

    onec_title: str | None
    """Точное Category.title из 1С; None — отдельного узла нет."""

    sort: int
    note: str = ""
    onec_code: str | None = None
    """Предпочтительный стабильный ключ 1С (Category.onec_code)."""

    slug: str | None = None
    """Запасной уникальный ключ сайта (Category.slug), из CSV где известен."""


# Реальные названия из storefront_source_categories_20261119.csv / иерархии 1С.
# slug/onec_code — где узел есть как строка CSV (лист или папка с прямыми товарами).
# Где узла нет — onec_title=None (не создаём).
MAIN_SECTION_SPECS: tuple[MainSectionSpec, ...] = (
    MainSectionSpec("Смартфоны", "1.1.Сотовые Телефоны", 10),
    MainSectionSpec("Планшеты", "1.2.Планшеты", 20),
    MainSectionSpec(
        "Чехлы и защита",
        "2.3.Чехлы",
        30,
        slug="23",
        note="В 1С нет единого «Чехлы и защита»; на витрине — папка 2.3.Чехлы. "
        "Стекла и плёнки — отдельные главные разделы.",
    ),
    MainSectionSpec("Стёкла (защита)", "2.1.Стекла", 31),
    MainSectionSpec(
        "Плёнки",
        "2.2.Пленки для плоттера Mocoll",
        32,
        slug="22-mocoll",
    ),
    MainSectionSpec(
        "Зарядки и кабели",
        "2.4.Зарядки/адаптеры",
        40,
        slug="24",
    ),
    MainSectionSpec(
        "Power Bank",
        "3.2.Доп.аккумуляторы",
        41,
        note="В 1С отдельные от зарядок; не объединяем.",
    ),
    MainSectionSpec("Наушники", "3.1.Наушники", 50),
    MainSectionSpec(
        "Apple AirPods",
        "2.5.Apple AirPods",
        51,
        slug="25apple-airpods",
    ),
    MainSectionSpec(
        "Samsung Buds",
        "2.7.Samsung Buds",
        52,
        slug="27samsung-buds",
    ),
    MainSectionSpec(
        "Умные часы",
        "3.3.Smart часы",
        60,
        slug="33smart",
    ),
    MainSectionSpec(
        "Apple Watch",
        "2.6.Apple Watch",
        61,
        slug="26apple-watch",
    ),
    MainSectionSpec(
        "Samsung Watch",
        "2.8.Samsung Watch",
        62,
        slug="28samsung-watch",
    ),
    MainSectionSpec(
        "Ремешки",
        "Ремешки",
        63,
        slug="00-00029251",
        onec_code="00-00029251",
    ),
    MainSectionSpec(
        "Портативная электроника",
        "Карманные роутеры",
        70,
        slug="00-00029274",
        onec_code="00-00029274",
        note="Отдельного раздела «Портативная электроника» в 1С нет; "
        "ближайший устойчивый узел — Карманные роутеры.",
    ),
    MainSectionSpec("Автоаксессуары", "3.4.АВТО-аксессуары", 80),
    MainSectionSpec(
        "Автомагнитолы",
        "Автомагнитолы",
        81,
        slug="00-00026085",
        onec_code="00-00026085",
        note="В 1С под «6.Бытовая техника», отдельная папка.",
    ),
    MainSectionSpec(
        "Колонки и акустика",
        "3.6.Динамики",
        90,
        slug="36",
    ),
    MainSectionSpec("Флешки и накопители", "3.5.Флешки/Жесткие диски", 100),
    MainSectionSpec(
        "Компьютеры и периферия",
        "Клавиатуры/мышки/коврики",
        110,
        slug="00-00002388",
        onec_code="00-00002388",
    ),
    MainSectionSpec("Ноутбуки", "7.Ноутбуки", 111),
    MainSectionSpec("Техника для дома", "6.Бытовая техника", 120),
    MainSectionSpec(
        "Dyson",
        "3.7.DYSON",
        130,
        slug="37dyson",
    ),
    MainSectionSpec(
        "Проекторы",
        "3.8.Проекторы",
        140,
        slug="38",
    ),
    MainSectionSpec(
        "Фототехника",
        "Фототехника",
        141,
        slug="00-00036008",
        onec_code="00-00036008",
    ),
    MainSectionSpec("Детские товары", "3.9.Детские товары", 150),
    MainSectionSpec(
        "Очки",
        "Очки",
        200,
        slug="00-00029237",
        onec_code="00-00029237",
    ),
    MainSectionSpec(
        "SIM-карты",
        "5.Сим карты",
        210,
        slug="5",
    ),
    MainSectionSpec(
        "Сопутствующие товары",
        None,
        220,
        note="Отдельной папки в 1С нет — раздел не создаём.",
    ),
    MainSectionSpec(
        "Услуги",
        None,
        230,
        note="Отдельной папки в 1С нет — раздел не создаём.",
    ),
)


def specs_with_onec_title() -> list[MainSectionSpec]:
    return [s for s in MAIN_SECTION_SPECS if s.onec_title]
