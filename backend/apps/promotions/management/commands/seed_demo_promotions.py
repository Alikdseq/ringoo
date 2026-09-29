"""
Демо-акции для витрины и ngrok (идемпотентно по title).
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.products.models import Category
from apps.promotions.models import Promotion

DEMO_PROMOTIONS = [
    {
        "title": "Скидка 20% на смартфоны",
        "description": "На iPhone и Android в наличии. Успей до конца акции.",
        "discount_type": Promotion.DISCOUNT_PERCENT,
        "discount_value": Decimal("20"),
        "category_slugs": ["iphone", "android"],
    },
    {
        "title": "−15% на наушники",
        "description": "AirPods и аксессуары для музыки каждый день.",
        "discount_type": Promotion.DISCOUNT_PERCENT,
        "discount_value": Decimal("15"),
        "category_slugs": ["airpods", "audio"],
    },
    {
        "title": "Рассрочка 0% на iPhone",
        "description": "Оформление в магазине Ringoo — без переплаты.",
        "discount_type": Promotion.DISCOUNT_PERCENT,
        "discount_value": Decimal("0"),
        "category_slugs": ["iphone"],
    },
    {
        "title": "Аксессуары по спеццене",
        "description": "Чехлы, стёкла и зарядки — выгоднее в комплекте.",
        "discount_type": Promotion.DISCOUNT_FIXED,
        "discount_value": Decimal("500"),
        "category_slugs": ["audio"],
    },
]


class Command(BaseCommand):
    help = "Создаёт активные демо-акции (идемпотентно по названию)."

    def handle(self, *args, **options):
        now = timezone.now()
        start = now - timedelta(days=1)
        end = now + timedelta(days=90)
        created = 0
        updated = 0

        for item in DEMO_PROMOTIONS:
            promo, was_created = Promotion.objects.get_or_create(
                title=item["title"],
                defaults={
                    "description": item["description"],
                    "discount_type": item["discount_type"],
                    "discount_value": item["discount_value"],
                    "start_date": start,
                    "end_date": end,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                promo.description = item["description"]
                promo.discount_type = item["discount_type"]
                promo.discount_value = item["discount_value"]
                promo.start_date = start
                promo.end_date = end
                promo.is_active = True
                promo.save(
                    update_fields=[
                        "description",
                        "discount_type",
                        "discount_value",
                        "start_date",
                        "end_date",
                        "is_active",
                        "updated_at",
                    ]
                )
                updated += 1

            slugs = item.get("category_slugs") or []
            if slugs:
                cats = Category.objects.filter(slug__in=slugs)
                promo.categories.set(cats)

        total = Promotion.objects.filter(is_active=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo promotions: created={created}, updated={updated}, active_total={total}"
            )
        )
