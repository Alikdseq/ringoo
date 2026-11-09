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
    """Позиция заказа: snapshot + цвет (FUNC-011)."""

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "product_title",
            "quantity",
            "price",
            "item_total",
            "color",
            "color_label",
            "color_slug",
            "color_hex",
        )
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """Заказ с вложенными items и валидацией."""

    items = OrderItemSerializer(many=True, read_only=True)
    has_rating = serializers.SerializerMethodField()
    can_pay = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()

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
            "closure_result",
            "display_status",
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
            "can_pay",
            "can_cancel",
            "payment_status",
        )
        read_only_fields = fields

    def get_has_rating(self, obj):
        return hasattr(obj, "manager_rating") and obj.manager_rating is not None

    def get_can_pay(self, obj) -> bool:
        from apps.payments.eligibility import evaluate_order_payment_eligibility

        return evaluate_order_payment_eligibility(obj).can_pay

    def get_can_cancel(self, obj) -> bool:
        from apps.orders.services import customer_may_cancel_order

        return customer_may_cancel_order(obj)

    def get_payment_status(self, obj) -> str | None:
        # Каноническое поле заказа; онлайн дополнительно сверяем с Payment.
        if obj.payment_status:
            return obj.payment_status
        latest = obj.payments.order_by("-created_at").only("status").first()
        return latest.status if latest else Order.PAYMENT_STATUS_UNPAID

    def get_display_status(self, obj) -> str:
        return obj.display_status_code()


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
    color_id = serializers.UUIDField(required=False, allow_null=True)
    # Цена с клиента не используется — подставляется из БД в OrderCreateSerializer.validate()
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )
    # FUNC-003: ожидаемая цена с витрины (price_at_add); при расхождении — price_changed.
    expected_unit_price = serializers.DecimalField(
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
    # FUNC-003: явное подтверждение актуальных серверных цен после предупреждения.
    accept_price_changes = serializers.BooleanField(required=False, default=False)

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
        from django.conf import settings

        # FUNC-007: списание только при явном BONUS_ENABLED (сейчас выкл.).
        if not bool(getattr(settings, "BONUS_ENABLED", False)):
            return Decimal("0")
        return Decimal("0")  # spend API не активирован даже при флаге — отдельное решение

    def validate_total_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("total_amount не может быть отрицательным.")
        return value

    def validate(self, attrs):
        delivery_type = attrs.get("delivery_type")
        store = attrs.get("store")
        payment_type = attrs.get("payment_type")

        # Банковский перевод оставлен в модели для истории заказов, но новые
        # заказы через API создавать нельзя (UI тоже скрывает этот способ).
        if payment_type == Order.PAYMENT_BANK_TRANSFER:
            raise serializers.ValidationError(
                {
                    "payment_type": (
                        "Способ оплаты «банковский перевод» недоступен для новых заказов. "
                        "Выберите наличные, карту при получении или онлайн-оплату."
                    )
                }
            )

        if delivery_type == Order.DELIVERY_DELIVERY:
            addr = attrs.get("delivery_address") or {}
            required = ("city", "street", "house")
            missing = [k for k in required if not addr.get(k)]
            if missing:
                raise serializers.ValidationError(
                    {"delivery_address": f"Для доставки укажите: {', '.join(required)}."}
                )
            if not store:
                raise serializers.ValidationError(
                    {
                        "store": (
                            "Для доставки укажите магазин комплектации, "
                            "в котором все товары корзины есть в наличии."
                        )
                    }
                )
        elif delivery_type == Order.DELIVERY_PICKUP:
            if not store:
                raise serializers.ValidationError(
                    {"store": "Для самовывоза укажите магазин."}
                )

        if store:
            if not Store.objects.filter(
                pk=store, is_active=True, is_warehouse=False
            ).exists():
                raise serializers.ValidationError(
                    {"store": "Магазин не найден или недоступен для заказа."}
                )

        items = attrs.get("items") or []
        if not items:
            return attrs

        from apps.products.models import ProductColor

        ids = [item["product_id"] for item in items]
        products = Product.objects.filter(id__in=ids, is_active=True).prefetch_related(
            "colors"
        )
        by_id = {p.id: p for p in products}
        missing_ids = set(ids) - set(by_id.keys())
        if missing_ids:
            raise serializers.ValidationError(
                {
                    "items": "Указаны неактивные или несуществующие товары. Обновите корзину и повторите заказ."
                }
            )

        color_ids = [
            item.get("color_id") for item in items if item.get("color_id")
        ]
        colors_by_id = {}
        if color_ids:
            for c in ProductColor.objects.filter(
                pk__in=color_ids, is_active=True
            ).select_related("product"):
                colors_by_id[c.id] = c

        resolved = []
        price_changes = []
        for idx, item in enumerate(items):
            p = by_id[item["product_id"]]
            qty = item["quantity"]
            color_id = item.get("color_id")
            color = None
            active_colors = [c for c in p.colors.all() if c.is_active]
            if color_id:
                color = colors_by_id.get(color_id)
                if color is None or color.product_id != p.id:
                    raise serializers.ValidationError(
                        {
                            "items": {
                                idx: {
                                    "color_id": (
                                        "Цвет не найден, неактивен или не "
                                        "относится к этому товару."
                                    )
                                }
                            }
                        }
                    )
                unit = Decimal(color.effective_price())
            else:
                if active_colors:
                    raise serializers.ValidationError(
                        {
                            "items": {
                                idx: {
                                    "color_id": (
                                        "Для этого товара необходимо выбрать цвет."
                                    )
                                }
                            }
                        }
                    )
                unit = Decimal(p.price)

            expected = item.get("expected_unit_price")
            if expected is not None and Decimal(expected) != unit:
                price_changes.append(
                    {
                        "product_id": str(p.id),
                        "product_title": p.title,
                        "color_id": str(color.id) if color else None,
                        "color_label": color.label if color else "",
                        "expected_unit_price": str(Decimal(expected)),
                        "actual_unit_price": str(unit),
                        "quantity": qty,
                    }
                )

            resolved.append(
                {
                    "product_id": p.id,
                    "quantity": qty,
                    "price": unit,
                    "color_id": color.id if color else None,
                    "color_label": color.label if color else "",
                    "color_slug": color.slug if color else "",
                    "color_hex": (color.hex or "") if color else "",
                }
            )

        if price_changes and not attrs.get("accept_price_changes"):
            raise serializers.ValidationError(
                {
                    "code": "price_changed",
                    "detail": (
                        "Цены в каталоге изменились. Подтвердите новый итог "
                        "(accept_price_changes=true)."
                    ),
                    "price_changes": price_changes,
                    "new_total_amount": str(
                        sum(r["price"] * r["quantity"] for r in resolved)
                    ),
                }
            )

        attrs["items"] = resolved

        # Стоимость доставки и итог — только сервер (клиентский delivery_cost/total игнорируются).
        delivery_cost = Decimal("0")
        attrs["delivery_cost"] = delivery_cost
        bonus_used = attrs.get("bonus_used") if attrs.get("bonus_used") is not None else Decimal("0")
        subtotal = sum(r["price"] * r["quantity"] for r in resolved)
        attrs["total_amount"] = subtotal + delivery_cost - bonus_used
        return attrs
