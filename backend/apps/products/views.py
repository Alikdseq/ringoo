"""
ViewSet для Category и View для Product (задачи 1.2.6, 1.2.7, 2.5.2, 2.5.3).
"""

import hashlib
from typing import ClassVar

from django.conf import settings
from django.core.cache import cache
from django.db.models import Exists, F, OuterRef, Prefetch, Q

from rest_framework import viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stores.models import Stock
from config.throttling import AnonReadRateThrottle, UserReadRateThrottle

from .catalog_filters import aggregate_product_models, apply_catalog_filters
from .cache_utils import (
    apply_public_cache_headers,
    autocomplete_cache_key,
    brands_cache_key,
    product_detail_cache_key,
    product_list_cache_key,
    product_models_cache_key,
)
from .models import Category, Product, ProductColor, ProductImage
from .search_synonyms import get_search_terms
from .serializers import (
    CategorySerializer,
    ProductAutocompleteSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


def _category_list_cache_key(request):
    """Ключ кэша списка категорий с учётом is_active."""
    version = cache.get("category_list_version") or 0
    is_active = request.query_params.get("is_active") or ""
    raw = f"is_active={is_active}"
    h = hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"category_list:v{version}:{h}"


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Список и детализация категорий.
    Фильтрация по is_active (по умолчанию только активные).
    Кэш списка на 10 минут (задача 2.5.3), инвалидация при изменении Category.
    Throttle (2.6.2): повышенный лимит для read-only.
    """

    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def list(self, request, *args, **kwargs):
        cache_key = _category_list_cache_key(request)
        timeout = getattr(settings, "CACHE_TIMEOUT_CATEGORIES", 600)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=timeout)
        return response

    def get_queryset(self):
        qs = Category.objects.all().order_by("sort_order", "title")
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1", "yes"):
                qs = qs.filter(is_active=True)
            elif is_active.lower() in ("false", "0", "no"):
                qs = qs.filter(is_active=False)
        else:
            qs = qs.filter(is_active=True)
        return qs


class ProductListPagination(PageNumberPagination):
    """Пагинация списка товаров (page_size для бесконечного скролла на клиенте)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ProductListView(ListAPIView):
    """
    Список товаров.
    Фильтры: category (slug), brand, min_price, max_price, search (по названию).
    Сортировка: ordering=popular|price_asc|price_desc|rating_desc|created_at.
    Фильтр rating_min — минимальный рейтинг (число, например 4).
    Пагинация (page + page_size; клиент может реализовать бесконечный скролл).
    Кэш на 5 минут (задача 2.5.2), инвалидация при изменении Product/Category.
    Throttle (2.6.2): повышенный лимит для read-only.
    """

    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = ProductListPagination
    filter_backends: ClassVar[list] = []
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def list(self, request, *args, **kwargs):
        cache_key = product_list_cache_key(request)
        timeout = getattr(
            settings,
            "CACHE_TIMEOUT_PRODUCTS_LIST",
            300,
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return apply_public_cache_headers(Response(cached))
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=timeout)
        return apply_public_cache_headers(response)

    def get_queryset(self):
        # Сортировка; для совместимости с cursor пагинацией основной порядок -created_at, id
        order = self.request.query_params.get("ordering", "created_at")
        base_order: tuple[str, ...]
        if order == "price_asc":
            base_order = ("price", "id")
        elif order == "price_desc":
            base_order = ("-price", "id")
        elif order == "rating_desc":
            base_order = ("-rating", "-created_at", "id")
        elif order == "popular":
            base_order = ("-reviews_count", "-rating", "-created_at", "id")
        else:
            base_order = ("-created_at", "id")

        qs = (
            Product.objects.filter(is_active=True, category__is_active=True)
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "colors",
                    queryset=ProductColor.objects.filter(is_active=True).order_by("sort_order", "label"),
                ),
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.select_related("color").order_by(
                        "sort_order", "created_at"
                    ),
                ),
                "stock_items",
            )
            .order_by(*base_order)
        )

        return apply_catalog_filters(qs, self.request.query_params)


class ProductModelsListView(APIView):
    """
    GET /api/v1/products/products/product-models/
    Линейки моделей в текущей выборке (те же фильтры, что у списка, без model).
    """

    permission_classes = [AllowAny]
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get(self, request):
        cache_key = product_models_cache_key(request)
        timeout = getattr(settings, "CACHE_TIMEOUT_PRODUCTS_LIST", 300)
        cached = cache.get(cache_key)
        if cached is not None:
            return apply_public_cache_headers(Response({"results": cached}))

        qs = Product.objects.filter(is_active=True, category__is_active=True)
        qs = apply_catalog_filters(qs, request.query_params, exclude_model=True)
        results = aggregate_product_models(qs)
        cache.set(cache_key, results, timeout=timeout)
        return apply_public_cache_headers(Response({"results": results}))


class ProductBrandsListView(APIView):
    """
    GET /api/v1/products/brands/ — список брендов (уникальные, непустые) для фильтра каталога.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get(self, request):
        cache_key = brands_cache_key()
        timeout = getattr(settings, "CACHE_TIMEOUT_CATEGORIES", 600)
        cached = cache.get(cache_key)
        if cached is not None:
            return apply_public_cache_headers(Response(cached))
        brands = list(
            Product.objects.filter(is_active=True, category__is_active=True)
            .exclude(brand__isnull=True)
            .exclude(brand="")
            .values_list("brand", flat=True)
            .distinct()
            .order_by("brand")
        )
        cache.set(cache_key, brands, timeout=timeout)
        return apply_public_cache_headers(Response(brands))


class ProductAutocompleteView(APIView):
    """
    GET /api/v1/products/autocomplete/?q=... — автодополнение по названию и артикулу (ТЗ).
    Возвращает до 10 товаров. Без пагинации, read-only throttle.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()[:100]
        if not q:
            return Response([])

        terms = get_search_terms(q)
        if not terms:
            return apply_public_cache_headers(Response([]))

        cache_key = autocomplete_cache_key(q)
        cached = cache.get(cache_key)
        if cached is not None:
            return apply_public_cache_headers(Response(cached))

        qs = (
            Product.objects.filter(is_active=True, category__is_active=True)
            .filter(
                Q(
                    *(
                        Q(title__icontains=term)
                        | Q(sku__icontains=term)
                        | Q(description__icontains=term)
                        for term in terms
                    ),
                    _connector=Q.OR,
                )
            )
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "colors",
                    queryset=ProductColor.objects.filter(is_active=True).order_by("sort_order", "label"),
                ),
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.select_related("color").order_by(
                        "sort_order", "created_at"
                    ),
                ),
            )[:10]
        )
        serializer = ProductAutocompleteSerializer(qs, many=True)
        data = serializer.data
        cache.set(cache_key, data, timeout=60)
        return apply_public_cache_headers(Response(data))


class ProductDetailView(RetrieveAPIView):
    """
    Детальная карточка товара.
    Все изображения, характеристики, наличие в магазинах (Stock), is_in_user_cart.
    Оптимизация запросов (2.5.4): select_related(category), prefetch_related(images, specs, stock_items).
    Throttle (2.6.2): повышенный лимит для read-only.
    """

    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.filter(is_active=True, category__is_active=True)
    lookup_url_kwarg = "slug"
    lookup_field = "slug"
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True, category__is_active=True)
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "colors",
                    queryset=ProductColor.objects.filter(is_active=True).order_by("sort_order", "label"),
                ),
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.select_related("color").order_by(
                        "sort_order", "created_at"
                    ),
                ),
                "specs",
                Prefetch("stock_items", queryset=Stock.objects.select_related("store")),
            )
        )

    def retrieve(self, request, *args, **kwargs):
        slug = kwargs.get(self.lookup_field) or kwargs.get("slug")
        cache_key = product_detail_cache_key(slug)
        timeout = getattr(settings, "CACHE_TIMEOUT_PRODUCTS_LIST", 300)
        cached = cache.get(cache_key)
        if cached is not None:
            return apply_public_cache_headers(Response(cached))
        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=timeout)
        return apply_public_cache_headers(response)
