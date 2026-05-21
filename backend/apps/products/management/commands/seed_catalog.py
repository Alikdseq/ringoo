"""
Заполнение БД тестовыми категориями и товарами (как на главной — кнопки категорий).
Категории: iPhone, iPad, Mac, Watch, AirPods, Android, Dyson, Консоли, Наушники.
В каждую категорию — по 5 товаров. Остатки (Stock) создаются для первых магазинов.
"""
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.products.models import Category, Product, ProductSpec
from apps.stores.models import Store, Stock


CATEGORIES = [
    ("iPhone", "iphone"),
    ("iPad", "ipad"),
    ("Mac", "mac"),
    ("Watch", "watch"),
    ("AirPods", "airpods"),
    ("Android", "android"),
    ("Dyson", "dyson"),
    ("Консоли", "playstation"),
    ("Наушники", "audio"),
]

PRODUCTS_BY_SLUG = {
    "iphone": [
        ("iPhone 15 Pro 256GB", "Смартфон Apple", "Apple", "APP-IP15P-256"),
        ("iPhone 15 128GB", "Смартфон Apple", "Apple", "APP-IP15-128"),
        ("iPhone 14 128GB", "Смартфон Apple", "Apple", "APP-IP14-128"),
        ("iPhone SE 64GB", "Компактный iPhone", "Apple", "APP-IPSE-64"),
        ("iPhone 15 Plus 256GB", "Большой экран", "Apple", "APP-IP15P-256"),
    ],
    "ipad": [
        ("iPad Pro 12.9 M2", "Планшет для творчества", "Apple", "APP-IPDP-129"),
        ("iPad Air 10.9", "Универсальный планшет", "Apple", "APP-IPDA-109"),
        ("iPad 10", "Базовый iPad", "Apple", "APP-IPD10"),
        ("iPad mini 8.3", "Компактный планшет", "Apple", "APP-IPDM-83"),
        ("iPad Pro 11 M2", "Планшет 11 дюймов", "Apple", "APP-IPDP-11"),
    ],
    "mac": [
        ("MacBook Pro 14 M3 Pro", "Ноутбук для профессионалов", "Apple", "APP-MBP14-M3P"),
        ("MacBook Air 13 M2", "Тонкий и лёгкий", "Apple", "APP-MBA13-M2"),
        ("iMac 24 M3", "Моноблок", "Apple", "APP-IMAC24-M3"),
        ("Mac mini M2", "Компактный десктоп", "Apple", "APP-MM-M2"),
        ("MacBook Pro 16 M3 Max", "Максимальная мощность", "Apple", "APP-MBP16-M3M"),
    ],
    "watch": [
        ("Apple Watch Ultra 2", "Часы для экстрима", "Apple", "APP-AWU2"),
        ("Apple Watch Series 9", "Умные часы", "Apple", "APP-AW9"),
        ("Apple Watch SE", "Доступные часы", "Apple", "APP-AWSE"),
        ("Apple Watch Hermès", "Часы премиум", "Apple", "APP-AWH"),
        ("Apple Watch Nike", "Для спорта", "Apple", "APP-AWN"),
    ],
    "airpods": [
        ("AirPods Pro 2", "Шумоподавление", "Apple", "APP-APP2"),
        ("AirPods 3", "Беспроводные наушники", "Apple", "APP-AP3"),
        ("AirPods Max", "Накладные наушники", "Apple", "APP-APM"),
        ("AirPods 2", "Классика", "Apple", "APP-AP2"),
        ("AirPods Pro USB-C", "Обновлённые Pro", "Apple", "APP-APP2C"),
    ],
    "android": [
        ("Samsung Galaxy S24 Ultra", "Флагман Samsung", "Samsung", "SAM-S24U"),
        ("Google Pixel 8 Pro", "Чистый Android", "Google", "GGL-P8P"),
        ("Xiaomi 14", "Флагман Xiaomi", "Xiaomi", "XIA-14"),
        ("OnePlus 12", "Быстрая зарядка", "OnePlus", "OP-12"),
        ("Samsung Galaxy A54", "Средний класс", "Samsung", "SAM-A54"),
    ],
    "dyson": [
        ("Dyson V15 Detect", "Беспроводной пылесос", "Dyson", "DYS-V15"),
        ("Dyson Airwrap", "Укладка волос", "Dyson", "DYS-AW"),
        ("Dyson Purifier Cool", "Очиститель воздуха", "Dyson", "DYS-PC"),
        ("Dyson Supersonic", "Фен", "Dyson", "DYS-SS"),
        ("Dyson Outsize", "Большой пылесос", "Dyson", "DYS-OUT"),
    ],
    "playstation": [
        ("PlayStation 5", "Игровая консоль", "Sony", "SONY-PS5"),
        ("PlayStation 5 Slim", "Компактная PS5", "Sony", "SONY-PS5S"),
        ("DualSense", "Геймпад PS5", "Sony", "SONY-DS"),
        ("PlayStation Portal", "Портативный экран", "Sony", "SONY-PSP"),
        ("PlayStation VR2", "VR-шлем", "Sony", "SONY-PSV2"),
    ],
    "audio": [
        ("Sony WH-1000XM5", "Наушники с шумоподавлением", "Sony", "SONY-XM5"),
        ("Bose QuietComfort 45", "Комфорт и тишина", "Bose", "BOSE-QC45"),
        ("Sennheiser Momentum 4", "Премиум звук", "Sennheiser", "SEN-M4"),
        ("JBL Tour One M2", "Беспроводные", "JBL", "JBL-TO2"),
        ("Apple AirPods Pro 2", "Для экосистемы Apple", "Apple", "APP-APP2"),
    ],
}


def make_price(base: int) -> Decimal:
    """Случайная цена около base (в рублях)."""
    return Decimal(str(base + random.randint(-500, 2000)))


class Command(BaseCommand):
    help = "Создать категории (как на главной) и по 5 товаров в каждую + остатки в магазинах"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Удалить все товары и категории перед созданием (осторожно)",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Удаление старых товаров и категорий...")
            Product.objects.all().delete()
            Category.objects.all().delete()
            Stock.objects.all().delete()

        categories_created = 0
        products_created = 0
        stocks_created = 0

        stores = list(Store.objects.filter(is_active=True)[:3])
        if not stores:
            self.stdout.write(self.style.WARNING("Нет активных магазинов. Остатки не создаются."))

        for title, slug in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "is_active": True,
                    "sort_order": categories_created,
                },
            )
            if created:
                categories_created += 1

            products_data = PRODUCTS_BY_SLUG.get(slug, [])
            if not products_data:
                products_data = [
                    (f"{title} Товар {i}", f"Описание {title} {i}", "Бренд", f"SKU-{slug}-{i}")
                    for i in range(1, 6)
                ]

            for i, (p_title, short_desc, brand, sku_base) in enumerate(products_data):
                base_slug = slugify(p_title, allow_unicode=False)
                if not base_slug:
                    base_slug = f"{slug}-{i+1}"
                product_slug = base_slug[:45]
                suffix = 0
                while Product.objects.filter(slug=product_slug).exists():
                    suffix += 1
                    product_slug = f"{base_slug[:40]}-{suffix}"[:50]
                sku = f"SEED-{slug}-{i+1}-{sku_base}"[:100]
                base_price = random.choice([19990, 29990, 49990, 79990, 99990, 129990, 149990])
                price = make_price(base_price)
                old_price = price + Decimal(str(random.randint(1000, 5000))) if random.random() > 0.5 else None
                product, p_created = Product.objects.get_or_create(
                    slug=product_slug,
                    defaults={
                        "title": p_title,
                        "sku": sku,
                        "short_description": short_desc,
                        "description": f"<p>{short_desc}. Тестовое описание товара.</p>",
                        "price": price,
                        "old_price": old_price,
                        "category": cat,
                        "brand": brand,
                        "is_active": True,
                        "is_featured": i == 0,
                        "rating": round(random.uniform(3.5, 5.0), 1),
                        "reviews_count": random.randint(0, 50),
                    },
                )
                if p_created:
                    products_created += 1
                    ProductSpec.objects.create(
                        product=product,
                        name="Гарантия",
                        value="1 год",
                        sort_order=0,
                    )
                    for store in stores:
                        qty = random.randint(0, 25)
                        if qty > 0:
                            _, stock_created = Stock.objects.get_or_create(
                                product=product,
                                store=store,
                                defaults={"quantity": qty, "reserved_quantity": 0},
                            )
                            if stock_created:
                                stocks_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: категорий создано {categories_created}, товаров {products_created}, остатков {stocks_created}"
            )
        )
