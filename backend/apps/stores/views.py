"""
API магазинов и остатков (задача 1.3.4).
"""

from django.db.models import Avg, Count, Exists, F, OuterRef, Prefetch, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from apps.orders.models import ManagerRating
from apps.products.models import Product, ProductColor, ProductImage
from apps.products.serializers import ProductListSerializer
from config.throttling import AnonReadRateThrottle, UserReadRateThrottle

from .models import Manager, Stock, Store, StoreImage
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


def _public_store_queryset():
    """
    Точки для покупателя: все активные Store.
    is_warehouse — метка «Склад»/Apple Room для UI, не исключение из витрины.
    """
    return Store.objects.filter(is_active=True)


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
            _public_store_queryset()
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
        store = get_object_or_404(
            Store, slug=self.kwargs["slug"], is_active=True
        )
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
    Публичные остатки в магазине (GET /api/v1/stores/{id}/stock/).

    ONEC-012: только активный магазин (включая «Склад»/is_warehouse);
    только активные товары; серии агрегируются; reserved не отдаётся.
    """

    permission_classes = [AllowAny]
    serializer_class = StockSerializer
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get_queryset(self):
        # list() отдаёт агрегаты; queryset нужен DRF для pagination metadata.
        store = get_object_or_404(Store, pk=self.kwargs.get("pk"), is_active=True)
        return (
            Stock.objects.filter(
                store_id=store.pk,
                product__is_active=True,
            )
            .select_related("product", "store")
            .order_by("product__title")
        )

    def list(self, request, *args, **kwargs):
        from rest_framework.response import Response

        store = get_object_or_404(Store, pk=self.kwargs.get("pk"), is_active=True)
        rows = Stock.aggregated_public_stock_for_store(store.pk)
        page = self.paginate_queryset(rows)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(rows)


class ProductStockView(ListAPIView):
    """
    Наличие товара во всех активных точках (GET /api/v1/products/{id}/stock/).
    Включая Apple Room / «Склад» (is_warehouse — метка для клиента).
    Несколько серий одного магазина агрегируются в одну строку (ONEC-010).
    """

    permission_classes = [AllowAny]
    serializer_class = StockSerializer
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get_queryset(self):
        product_id = self.kwargs.get("pk")
        return (
            Stock.objects.filter(
                product_id=product_id,
                store__is_active=True,
            )
            .select_related("product", "store")
            .order_by("store__city", "store__name")
        )

    def list(self, request, *args, **kwargs):
        from rest_framework.response import Response

        product_id = self.kwargs.get("pk")
        rows = Stock.aggregated_public_stock_for_product(product_id)
        page = self.paginate_queryset(rows)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(rows)
