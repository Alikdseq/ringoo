"""
Сериализаторы промокодов и акций (валидация, список акций).
"""

from decimal import Decimal

from rest_framework import serializers

from .models import Promotion


class PromotionListSerializer(serializers.ModelSerializer):
    """Акция для списка: id, title, description, image, discount_*, dates, category_slugs."""

    category_slugs = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = (
            "id",
            "title",
            "description",
            "image",
            "discount_type",
            "discount_value",
            "start_date",
            "end_date",
            "category_slugs",
            "created_at",
        )
        read_only_fields = fields

    def get_category_slugs(self, obj):
        return list(obj.categories.values_list("slug", flat=True))


class PromoCodeValidateSerializer(serializers.Serializer):
    """Вход для проверки промокода: code, order_amount."""

    code = serializers.CharField(max_length=64, trim_whitespace=True)
    order_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
    )
