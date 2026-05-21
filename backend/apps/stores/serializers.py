"""
Сериализаторы магазинов (задача 1.3.3).
"""

from rest_framework import serializers

from apps.orders.models import ManagerRating
from config.public_urls import absolute_media_url

from .models import Manager, Store, Stock, StoreImage


def _absolute_media_url(request, file_field):
    if not file_field:
        return None
    return absolute_media_url(request, file_field.url)


class StoreSerializer(serializers.ModelSerializer):
    """Магазин: id, name, slug, address, city, phone, coordinates, working_hours."""

    coordinates = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = (
            "id",
            "name",
            "slug",
            "address",
            "city",
            "phone",
            "coordinates",
            "working_hours",
        )
        read_only_fields = fields

    def get_coordinates(self, obj):
        """Координаты для карты: {latitude, longitude} или null."""
        if obj.latitude is not None and obj.longitude is not None:
            return {
                "latitude": str(obj.latitude),
                "longitude": str(obj.longitude),
            }
        return None


class StoreDetailSerializer(StoreSerializer):
    """Магазин с полями для детальной страницы (email, is_active и т.д.)."""

    coordinates = serializers.SerializerMethodField()

    class Meta(StoreSerializer.Meta):
        model = Store
        fields = (  # type: ignore[assignment]
            "id",
            "name",
            "slug",
            "address",
            "city",
            "phone",
            "email",
            "coordinates",
            "working_hours",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields  # type: ignore[assignment]


class StoreImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = StoreImage
        fields = ("id", "image", "alt_text", "sort_order")
        read_only_fields = fields

    def get_image(self, obj):
        return _absolute_media_url(self.context.get("request"), obj.image)


class ManagerBriefSerializer(serializers.ModelSerializer):
    """Краткая карточка менеджера на странице магазина."""

    photo = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True, default=0.0)
    ratings_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Manager
        fields = (
            "id",
            "name",
            "slug",
            "job_title",
            "photo",
            "average_rating",
            "ratings_count",
        )
        read_only_fields = fields

    def get_photo(self, obj):
        return _absolute_media_url(self.context.get("request"), obj.photo)


class StorePageSerializer(StoreSerializer):
    """Публичная страница магазина по slug."""

    images = serializers.SerializerMethodField()
    managers = serializers.SerializerMethodField()

    class Meta(StoreSerializer.Meta):
        fields = (  # type: ignore[assignment]
            "id",
            "name",
            "slug",
            "address",
            "city",
            "phone",
            "email",
            "coordinates",
            "working_hours",
            "description",
            "meta_title",
            "meta_description",
            "images",
            "managers",
        )
        read_only_fields = fields  # type: ignore[assignment]

    def get_images(self, obj):
        images = obj.images.filter(is_active=True).order_by("sort_order", "id")
        return StoreImageSerializer(images, many=True, context=self.context).data

    def get_managers(self, obj):
        managers = getattr(obj, "active_managers", None)
        if managers is None:
            managers = obj.managers.filter(is_active=True).order_by("order", "name")
        return ManagerBriefSerializer(managers, many=True, context=self.context).data


class ManagerStoreSerializer(serializers.ModelSerializer):
    """Краткие данные магазина для карточки менеджера."""

    class Meta:
        model = Store
        fields = ("id", "name", "slug", "address", "city")
        read_only_fields = fields


class ManagerSerializer(serializers.ModelSerializer):
    """Менеджер с магазином и рейтингом (для «О нас» и формы оценки)."""

    store = ManagerStoreSerializer(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    ratings_count = serializers.IntegerField(read_only=True)
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Manager
        fields = (
            "id",
            "name",
            "slug",
            "job_title",
            "photo",
            "store",
            "average_rating",
            "ratings_count",
        )
        read_only_fields = fields

    def get_photo(self, obj):
        return _absolute_media_url(self.context.get("request"), obj.photo)


class ManagerDetailSerializer(serializers.ModelSerializer):
    """Публичная страница менеджера по slug."""

    store = ManagerStoreSerializer(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    ratings_count = serializers.IntegerField(read_only=True)
    photo = serializers.SerializerMethodField()
    photo_2 = serializers.SerializerMethodField()

    class Meta:
        model = Manager
        fields = (
            "id",
            "name",
            "slug",
            "job_title",
            "bio",
            "photo",
            "photo_alt",
            "photo_2",
            "photo_2_alt",
            "store",
            "average_rating",
            "ratings_count",
        )
        read_only_fields = fields

    def get_photo(self, obj):
        return _absolute_media_url(self.context.get("request"), obj.photo)

    def get_photo_2(self, obj):
        return _absolute_media_url(self.context.get("request"), obj.photo_2)


class ManagerReviewSerializer(serializers.ModelSerializer):
    """Публичный отзыв о менеджере (без персональных данных заказа)."""

    class Meta:
        model = ManagerRating
        fields = ("id", "rating", "comment", "created_at")
        read_only_fields = fields


class StockSerializer(serializers.ModelSerializer):
    """Остаток: product, store, quantity, available_quantity."""

    available_quantity = serializers.ReadOnlyField()

    class Meta:
        model = Stock
        fields = ("product", "store", "quantity", "available_quantity")
        read_only_fields = fields
