"""
Сериализаторы заказов (задача 1.5.3).
"""

from decimal import Decimal

from rest_framework import serializers

from apps.products.models import Product
from apps.stores.models import Store

from .delivery_address import normalize_delivery_address
from .models import ManagerRating, Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Позиция заказа: id, product_title, quantity, price, item_total."""

    class Meta:
        model = OrderItem
        fields = ("id", "product_title", "quantity", "price", "item_total")
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """Заказ с вложенными items и валидацией."""

    items = OrderItemSerializer(many=True, read_only=True)
    has_rating = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "full_name",
            "phone",
            "email",
            "delivery_type",
            "delivery_address",
            "store",
            "payment_type",
            "status",
            "total_amount",
            "delivery_cost",
            "bonus_used",
            "bonus_earned",
            "comment",
            "consent_personal_data",
            "items",
            "created_at",
            "updated_at",
            "has_rating",
        )
        read_only_fields = fields

    def get_has_rating(self, obj):
        return hasattr(obj, "manager_rating") and obj.manager_rating is not None


class ManagerRatingSerializer(serializers.ModelSerializer):
    """Оценка менеджера: для ответа и для публичного списка."""

    order_number = serializers.CharField(source="order.order_number", read_only=True)
    manager_name = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()

    class Meta:
        model = ManagerRating
        fields = (
            "id",
            "order",
            "order_number",
            "manager",
            "manager_name",
            "store_name",
            "rating",
            "comment",
            "created_at",
        )
        read_only_fields = fields

    def get_manager_name(self, obj):
        return obj.manager.name if obj.manager_id else None

    def get_store_name(self, obj):
        return obj.manager.store.name if obj.manager_id else None


class ManagerRatingCreateSerializer(serializers.Serializer):
    """Отправка оценки: order_id/order_number+phone, manager_id (конкретный менеджер), rating, comment."""

    order_number = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    order_id = serializers.UUIDField(required=False)
    manager_id = serializers.UUIDField(required=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class OrderItemCreateSerializer(serializers.Serializer):
    """Одна позиция для создания заказа."""

    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=999)
    # Цена с клиента не используется — подставляется из БД в OrderCreateSerializer.validate()
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )


class OrderCreateSerializer(serializers.Serializer):
    """
    Создание заказа.
    Цены позиций и итоговая сумма берутся с сервера (каталог), а не из тела запроса.
    Поле bonus_used принимается для совместимости API, но списание бонусов отключено (всегда 0).
    """

    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=50)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    delivery_type = serializers.ChoiceField(choices=Order.DELIVERY_CHOICES)
    delivery_address = serializers.JSONField(required=False, allow_null=True, default=dict)
    store = serializers.UUIDField(required=False, allow_null=True)
    payment_type = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES)
    items = OrderItemCreateSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    delivery_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), default=Decimal("0")
    )
    bonus_used = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), default=Decimal("0")
    )
    comment = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=5000
    )
    consent_personal_data = serializers.BooleanField(required=True)
    consent_marketing = serializers.BooleanField(required=False, default=False)

    def validate_consent_personal_data(self, value):
        if not value:
            raise serializers.ValidationError(
                "Необходимо согласие на обработку персональных данных."
            )
        return value

    def validate_delivery_address(self, value):
        if value is None:
            return {}
        return normalize_delivery_address(value)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Список товаров не может быть пустым.")
        return value

    def validate_bonus_used(self, value):
        if value < 0:
            raise serializers.ValidationError("bonus_used не может быть отрицательным.")
        # Бонусная программа временно скрыта: не списываем бонусы через этот API.
        return Decimal("0")

    def validate_total_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("total_amount не может быть отрицательным.")
        return value

    def validate(self, attrs):
        delivery_type = attrs.get("delivery_type")
        store = attrs.get("store")

        if delivery_type == Order.DELIVERY_DELIVERY:
            if store:
                raise serializers.ValidationError(
                    {"store": "Для доставки поле «магазин» не указывается."}
                )
            attrs["store"] = None
            addr = attrs.get("delivery_address") or {}
            required = ("city", "street", "house")
            missing = [k for k in required if not addr.get(k)]
            if missing:
                raise serializers.ValidationError(
                    {"delivery_address": f"Для доставки укажите: {', '.join(required)}."}
                )
        elif delivery_type == Order.DELIVERY_PICKUP:
            if not store:
                raise serializers.ValidationError(
                    {"store": "Для самовывоза укажите магазин."}
                )
            if not Store.objects.filter(pk=store, is_active=True).exists():
                raise serializers.ValidationError(
                    {"store": "Магазин не найден или недоступен для заказа."}
                )

        items = attrs.get("items") or []
        if not items:
            return attrs

        ids = [item["product_id"] for item in items]
        products = Product.objects.filter(id__in=ids, is_active=True)
        by_id = {p.id: p for p in products}
        missing_ids = set(ids) - set(by_id.keys())
        if missing_ids:
            raise serializers.ValidationError(
                {
                    "items": "Указаны неактивные или несуществующие товары. Обновите корзину и повторите заказ."
                }
            )

        resolved = []
        for item in items:
            p = by_id[item["product_id"]]
            qty = item["quantity"]
            unit = Decimal(p.price)
            resolved.append(
                {
                    "product_id": p.id,
                    "quantity": qty,
                    "price": unit,
                }
            )
        attrs["items"] = resolved

        delivery_cost = attrs.get("delivery_cost") if attrs.get("delivery_cost") is not None else Decimal("0")
        bonus_used = attrs.get("bonus_used") if attrs.get("bonus_used") is not None else Decimal("0")
        subtotal = sum(r["price"] * r["quantity"] for r in resolved)
        attrs["total_amount"] = subtotal + delivery_cost - bonus_used
        return attrs
