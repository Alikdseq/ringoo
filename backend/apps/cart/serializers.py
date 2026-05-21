"""
Сериализаторы корзины (задача 1.4.3).
"""

from rest_framework import serializers

from apps.products.serializers import ProductColorSerializer, ProductListSerializer
from apps.stores.serializers import StoreSerializer

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """
    Позиция корзины: product (nested), store (nested, nullable), color, item_total.
    """

    product = ProductListSerializer(read_only=True)
    store = StoreSerializer(read_only=True, allow_null=True)
    color = ProductColorSerializer(read_only=True, allow_null=True)
    item_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "store",
            "color",
            "quantity",
            "price_at_add",
            "item_total",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_item_total(self, obj):
        return obj.get_total()


class CartSerializer(serializers.ModelSerializer):
    """
    Корзина: items (nested CartItemSerializer), total_amount.
    """

    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "total_amount", "created_at", "updated_at")
        read_only_fields = fields

    def get_total_amount(self, obj):
        return obj.get_total()


class CartItemCreateSerializer(serializers.Serializer):
    """Добавление товара в корзину: product (id), quantity, store (id, optional), color (id, optional)."""

    product = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=999)
    store = serializers.UUIDField(required=False, allow_null=True)
    color = serializers.UUIDField(required=False, allow_null=True)

    def validate_product(self, value):
        from apps.products.models import Product

        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Товар не найден или не активен.")
        return value

    def validate_store(self, value):
        if value is None:
            return value
        from apps.stores.models import Store

        if not Store.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Магазин не найден или не активен.")
        return value

    def validate(self, attrs):
        from apps.products.models import Product, ProductColor

        product_id = attrs["product"]
        color_id = attrs.get("color")
        if color_id is None:
            return attrs
        try:
            color = ProductColor.objects.select_related("product").get(
                pk=color_id, is_active=True, product_id=product_id
            )
        except ProductColor.DoesNotExist:
            raise serializers.ValidationError(
                {"color": "Цвет не найден или не относится к этому товару."}
            )
        attrs["_color_obj"] = color
        return attrs


class CartItemUpdateSerializer(serializers.ModelSerializer):
    """Изменение количества в позиции корзины (0 — удалить позицию)."""

    class Meta:
        model = CartItem
        fields = ("quantity",)

    quantity = serializers.IntegerField(min_value=0)
