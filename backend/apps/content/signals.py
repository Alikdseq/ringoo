"""
Сигналы контента: пересчёт рейтинга товара при сохранении/удалении отзыва (задача 2.2.3).
"""

from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save

from .models import Review


def _recalculate_product_rating(product_id):
    """Пересчитать rating и reviews_count у товара по одобренным отзывам."""
    from apps.products.models import Product

    agg = Review.objects.filter(
        product_id=product_id,
        is_approved=True,
    ).aggregate(
        avg_rating=Avg("rating"),
        count=Count("id"),
    )
    avg = agg["avg_rating"]
    count = agg["count"] or 0
    Product.objects.filter(pk=product_id).update(
        rating=round(avg, 2) if avg is not None else 0.0,
        reviews_count=count,
    )


def on_review_saved(sender, instance, **kwargs):
    if instance.product_id:
        _recalculate_product_rating(instance.product_id)


def on_review_deleted(sender, instance, **kwargs):
    if instance.product_id:
        _recalculate_product_rating(instance.product_id)
