"""Скопировать price/old_price товара в варианты цвета без своей цены."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.products.models import ProductColor


class Command(BaseCommand):
    help = "Заполнить ProductColor.price из Product.price, если у цвета цена не задана."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-empty",
            action="store_true",
            default=True,
            help="Обновлять только записи без price (по умолчанию)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Перезаписать price у всех активных цветов",
        )

    def handle(self, *args, **options):
        only_empty = options["only_empty"] and not options["force"]
        qs = ProductColor.objects.filter(is_active=True).select_related("product")
        updated = 0
        for color in qs.iterator():
            product = color.product
            if only_empty and color.price is not None:
                continue
            new_price = product.price
            new_old = product.old_price
            if new_price is None and new_old is None:
                continue
            color.price = new_price
            color.old_price = new_old
            color.save(update_fields=["price", "old_price"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Обновлено цветов: {updated}"))
