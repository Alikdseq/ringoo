"""
Сериализаторы избранного. Возвращаем список товаров в формате каталога.
"""

from rest_framework import serializers

from apps.products.serializers import ProductListSerializer

from .models import WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    """Элемент избранного с вложенным товаром."""

    product = ProductListSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ("id", "product", "created_at")


class WishlistItemCreateSerializer(serializers.Serializer):
    """Добавление товара в избранное: только product_id."""

    product_id = serializers.UUIDField()

    def validate_product_id(self, value):
        from apps.products.models import Product

        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Товар не найден или не активен.")
        return value
