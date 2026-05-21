"""
Удаление тестового каталога: товары вне категорий iphone и samsung, деактивация остальных категорий.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Category, Product


ALLOWED_CATEGORY_SLUGS = frozenset({
    "iphone",
    "samsung",
    "huawei",
    "infinix",
    "realme",
    "tecno",
    "xiaomi",
})


class Command(BaseCommand):
    help = (
        "Удаляет товары: по умолчанию — все вне категорий каталога public. "
        "С флагом --all-products — удаляет вообще все товары (перед импортом из public). "
        "Категории вне whitelist помечает is_active=False."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать числа без удаления",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Подтвердить удаление (без интерактива)",
        )
        parser.add_argument(
            "--all-products",
            action="store_true",
            help="Удалить все товары (включая iphone/samsung), затем деактивировать лишние категории.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        yes = options["yes"]
        all_products = options["all_products"]
        if not dry and not yes:
            self.stderr.write("Укажите --yes для выполнения или --dry-run для просмотра.")
            return

        if all_products:
            qs_bad_products = Product.objects.all()
        else:
            qs_bad_products = Product.objects.exclude(category__slug__in=ALLOWED_CATEGORY_SLUGS)
        bad_count = qs_bad_products.count()
        qs_bad_cats = Category.objects.exclude(slug__in=ALLOWED_CATEGORY_SLUGS)
        cat_count = qs_bad_cats.count()

        if all_products:
            self.stdout.write(f"Товаров к удалению (все): {bad_count}")
        else:
            self.stdout.write(f"Товаров к удалению (вне iphone/samsung): {bad_count}")
        self.stdout.write(f"Категорий к деактивации: {cat_count}")

        if dry:
            self.stdout.write(self.style.WARNING("dry-run — изменений нет"))
            return

        with transaction.atomic():
            deleted, _ = qs_bad_products.delete()
            self.stdout.write(self.style.SUCCESS(f"Удалено объектов (каскад): {deleted}"))
            updated = qs_bad_cats.update(is_active=False)
            self.stdout.write(self.style.SUCCESS(f"Категорий деактивировано: {updated}"))
            Category.objects.filter(slug__in=ALLOWED_CATEGORY_SLUGS).update(is_active=True)

        self.stdout.write(self.style.SUCCESS("Готово."))
