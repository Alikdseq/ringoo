"""
API магазинов и остатков (задача 1.3.4).
"""

from django.db.models import Avg, Count, Exists, F, OuterRef, Prefetch, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from apps.products.models import Product, ProductColor, ProductImage
from apps.products.serializers import ProductListSerializer
from apps.orders.models import ManagerRating
from config.throttling import AnonReadRateThrottle, UserReadRateThrottle

from .models import Manager, Store, Stock, StoreImage
from .serializers import (
    ManagerDetailSerializer,
    ManagerReviewSerializer,
    ManagerSerializer,
    StockSerializer,
    StoreDetailSerializer,
    StorePageSerializer,
    StoreSerializer,
)


def _manager_queryset_with_ratings():
    return Manager.objects.filter(is_active=True).select_related("store").annotate(
        average_rating=Coalesce(Avg("ratings__rating"), Value(0.0)),
        ratings_count=Count("ratings"),
    )


class ManagerListView(ListAPIView):
    """
    Список менеджеров с магазином и рейтингом (GET /api/v1/stores/managers/).
    """

    permission_classes = [AllowAny]
    serializer_class = ManagerSerializer
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]
    pagination_class = None

    def get_queryset(self):
        return _manager_queryset_with_ratings().order_by(
            "store__city", "store__name", "order", "name"
        )


class ManagerDetailBySlugView(RetrieveAPIView):
    """GET /api/v1/stores/managers/by-slug/{slug}/"""

    permission_classes = [AllowAny]
    serializer_class = ManagerDetailSerializer
    lookup_field = "slug"
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get_queryset(self):
        return _manager_queryset_with_ratings()


class ManagerReviewsBySlugView(ListAPIView):
    """GET /api/v1/stores/managers/by-slug/{slug}/reviews/"""

    permission_classes = [AllowAny]
    serializer_class = ManagerReviewSerializer
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]
    pagination_class = None

    def get_queryset(self):
        manager = get_object_or_404(
            Manager.objects.filter(is_active=True),
            slug=self.kwargs["slug"],
        )
        return (
            ManagerRating.objects.filter(manager=manager)
            .exclude(comment__isnull=True)
            .exclude(comment="")
            .order_by("-created_at")
        )


class StoreListView(ListAPIView):
    """
    Список магазинов (GET /api/v1/stores/).
    """

    permission_classes = [AllowAny]
    serializer_class = StoreSerializer
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get_queryset(self):
        qs = Store.objects.all().order_by("city", "name")
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if str(is_active).lower() in ("true", "1", "yes"):
                qs = qs.filter(is_active=True)
            elif str(is_active).lower() in ("false", "0", "no"):
                qs = qs.filter(is_active=False)
        else:
            qs = qs.filter(is_active=True)
        city = self.request.query_params.get("city", "").strip()
        if city:
            qs = qs.filter(city__icontains=city)
        return qs


class StoreBySlugView(RetrieveAPIView):
    """GET /api/v1/stores/by-slug/{slug}/"""

    permission_classes = [AllowAny]
    serializer_class = StorePageSerializer
    lookup_field = "slug"
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get_queryset(self):
        managers_qs = _manager_queryset_with_ratings().order_by("order", "name")
        return (
            Store.objects.filter(is_active=True)
            .prefetch_related(
                Prefetch("images", queryset=StoreImage.objects.filter(is_active=True)),
                Prefetch("managers", queryset=managers_qs, to_attr="active_managers"),
            )
        )


class StoreDetailView(RetrieveAPIView):
    """
    Детали магазина (GET /api/v1/stores/{id}/).
    """

    permission_classes = [AllowAny]
    serializer_class = StoreDetailSerializer
    queryset = Store.objects.all()
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]


class StoreProductsBySlugView(ListAPIView):
    """GET /api/v1/stores/by-slug/{slug}/products/ — товары в наличии в магазине."""

    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get_queryset(self):
        store = get_object_or_404(Store, slug=self.kwargs["slug"], is_active=True)
        has_stock = Stock.objects.filter(
            product_id=OuterRef("pk"),
            store=store,
        ).filter(quantity__gt=F("reserved_quantity"))
        return (
            Product.objects.filter(is_active=True, category__is_active=True)
            .filter(Exists(has_stock))
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "colors",
                    queryset=ProductColor.objects.filter(is_active=True).order_by(
                        "sort_order", "label"
                    ),
                ),
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.select_related("color").order_by(
                        "sort_order", "created_at"
                    ),
                ),
                "stock_items",
            )
            .order_by("-created_at", "id")
        )


class StockListView(ListAPIView):
    """
    Остатки в магазине (GET /api/v1/stores/{id}/stock/).
    """

    permission_classes = [AllowAny]
    serializer_class = StockSerializer

    def get_queryset(self):
        store_id = self.kwargs.get("pk")
        return (
            Stock.objects.filter(store_id=store_id)
            .select_related("product", "store")
            .order_by("product__title")
        )


class ProductStockView(ListAPIView):
    """
    Наличие товара во всех магазинах (GET /api/v1/products/{id}/stock/).
    """

    permission_classes = [AllowAny]
    serializer_class = StockSerializer

    def get_queryset(self):
        product_id = self.kwargs.get("pk")
        return (
            Stock.objects.filter(product_id=product_id)
            .select_related("product", "store")
            .order_by("store__city", "store__name")
        )
