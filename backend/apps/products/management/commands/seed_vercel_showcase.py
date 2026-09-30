"""Пять карточек витрины с фото из catalog_media. Идемпотентно по slug."""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.products.models import Category, Product, ProductColor, ProductImage
from apps.stores.models import Stock, Store

SHOWCASE = [
    {
        "slug": "xiaomi-15",
        "title": "Xiaomi 15",
        "brand": "Xiaomi",
        "sku": "VITRINE-XIAOMI-15",
        "price": "69990.00",
        "old_price": "79990.00",
        "folder": "xiaomi-15",
        "color_slug": "black",
        "color_label": "Чёрный",
        "hex": "#1A1A1A",
        "short": "Флагман Xiaomi с основной камерой Leica.",
    },
    {
        "slug": "iphone-17-pro",
        "title": "iPhone 17 Pro",
        "brand": "Apple",
        "sku": "VITRINE-IPHONE-17-PRO",
        "price": "129990.00",
        "old_price": "139990.00",
        "folder": "iphone-17-pro",
        "color_slug": "orange",
        "color_label": "Оранжевый",
        "hex": "#E8772E",
        "short": "iPhone 17 Pro. Фото корпуса и камеры.",
    },
    {
        "slug": "huawei-pura-80",
        "title": "Huawei Pura 80",
        "brand": "Huawei",
        "sku": "VITRINE-HUAWEI-PURA-80",
        "price": "89990.00",
        "old_price": "99990.00",
        "folder": "huawei-pura-80",
        "color_slug": "black",
        "color_label": "Чёрный",
        "hex": "#111111",
        "short": "Huawei Pura 80. Фото из каталога.",
    },
    {
        "slug": "samsung-galaxy-a07",
        "title": "Samsung Galaxy A07",
        "brand": "Samsung",
        "sku": "VITRINE-SAMSUNG-A07",
        "price": "12990.00",
        "old_price": "14990.00",
        "folder": "samsung-a07",
        "color_slug": "black",
        "color_label": "Чёрный",
        "hex": "#222222",
        "short": "Samsung Galaxy A07.",
    },
    {
        "slug": "realme-14t",
        "title": "realme 14T",
        "brand": "realme",
        "sku": "VITRINE-REALME-14T",
        "price": "24990.00",
        "old_price": "27990.00",
        "folder": "realme-14t",
        "color_slug": "green",
        "color_label": "Зелёный",
        "hex": "#3D7A4A",
        "short": "realme 14T.",
    },
]


def _image_paths(folder: str) -> list[Path]:
    root = Path(settings.BASE_DIR) / "catalog_media" / "catalog" / folder
    if not root.is_dir():
        return []
    files = [p for p in root.iterdir() if p.is_file() and not p.name.startswith(".")]
    def sort_key(path: Path) -> tuple:
        name = path.name.lower()
        front = 0 if "front" in name else 1
        return (front, name)
    return sorted(files, key=sort_key)


class Command(BaseCommand):
    help = "Создаёт 5 товаров витрины и привязывает фото из catalog_media."

    def handle(self, *args, **options):
        category, _ = Category.objects.get_or_create(
            slug="smartphones",
            defaults={
                "title": "Смартфоны",
                "is_active": True,
                "sort_order": 0,
            },
        )
        if not category.is_active:
            category.is_active = True
            category.save(update_fields=["is_active"])

        store, _ = Store.objects.get_or_create(
            slug="ringoo-main",
            defaults={
                "name": "Ringoo",
                "address": "Москва",
                "city": "Москва",
                "is_active": True,
            },
        )

        created = 0
        for row in SHOWCASE:
            product, was_created = Product.objects.get_or_create(
                slug=row["slug"],
                defaults={
                    "title": row["title"],
                    "sku": row["sku"],
                    "brand": row["brand"],
                    "price": Decimal(row["price"]),
                    "old_price": Decimal(row["old_price"]),
                    "category": category,
                    "short_description": row["short"],
                    "description": row["short"],
                    "is_active": True,
                    "is_featured": True,
                    "rating": 4.8,
                    "reviews_count": 12,
                },
            )
            if was_created:
                created += 1
            else:
                product.is_active = True
                product.is_featured = True
                product.category = category
                product.price = Decimal(row["price"])
                product.old_price = Decimal(row["old_price"])
                product.save(
                    update_fields=[
                        "is_active",
                        "is_featured",
                        "category",
                        "price",
                        "old_price",
                    ]
                )

            color, _ = ProductColor.objects.get_or_create(
                product=product,
                slug=row["color_slug"],
                defaults={
                    "label": row["color_label"],
                    "hex": row["hex"],
                    "sort_order": 0,
                    "is_active": True,
                },
            )

            paths = _image_paths(row["folder"])
            if not paths:
                self.stdout.write(self.style.WARNING(f"Нет фото для {row['slug']}"))
            else:
                product.images.all().delete()
                for index, path in enumerate(paths):
                    rel = f"catalog/{row['folder']}/{path.name}"
                    image = ProductImage(
                        product=product,
                        color=color,
                        is_main=(index == 0),
                        alt_text=row["title"],
                        sort_order=index,
                    )
                    image.image.name = rel
                    image.save()

            Stock.objects.update_or_create(
                product=product,
                store=store,
                defaults={"quantity": 8, "reserved_quantity": 0},
            )
            self.stdout.write(f"{row['slug']}: {len(paths)} photos")

        self.stdout.write(self.style.SUCCESS(f"Showcase ready, new products: {created}"))
