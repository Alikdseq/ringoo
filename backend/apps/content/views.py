"""
API контента: Article, News, Review (задача 2.2.6).
ViewSets с фильтрацией, поиском, пагинацией.
"""

from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from config.throttling import AnonReadRateThrottle, UserReadRateThrottle

from .models import Article, News, PageGalleryImage, Review, Tag
from .serializers import (
    ArticleListSerializer,
    ArticleSerializer,
    NewsListSerializer,
    NewsSerializer,
    PageGalleryImageSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
    TagSerializer,
)


class ContentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Список и детали тегов. Throttle (2.6.2): повышенный лимит для read-only."""

    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Список и детали статей блога.
    Фильтры: is_published, category, tag (slug).
    Поиск: search по title, excerpt, content.
    Throttle (2.6.2): повышенный лимит для read-only.
    """

    permission_classes = (AllowAny,)
    pagination_class = ContentPagination
    filter_backends = (SearchFilter,)
    search_fields = ("title", "excerpt", "content")
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    lookup_value_regex = "[^/.]+"

    def get_queryset(self):
        qs = (
            Article.objects.all()
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-published_at", "-created_at")
        )
        is_published = self.request.query_params.get("is_published")
        if is_published is not None:
            if str(is_published).lower() in ("true", "1", "yes"):
                qs = qs.filter(is_published=True)
            elif str(is_published).lower() in ("false", "0", "no"):
                qs = qs.filter(is_published=False)
        else:
            qs = qs.filter(is_published=True)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        tag_slug = self.request.query_params.get("tag")
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        return qs.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return ArticleListSerializer
        return ArticleSerializer


class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Список и детали новостей.
    Фильтры: is_published, is_featured, category, tag.
    Поиск: search по title, excerpt, content.
    Throttle (2.6.2): повышенный лимит для read-only.
    """

    permission_classes = (AllowAny,)
    pagination_class = ContentPagination
    filter_backends = (SearchFilter,)
    search_fields = ("title", "excerpt", "content")
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    lookup_value_regex = "[^/.]+"

    def get_queryset(self):
        qs = (
            News.objects.all()
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-published_at", "-created_at")
        )
        is_published = self.request.query_params.get("is_published")
        if is_published is not None:
            if str(is_published).lower() in ("true", "1", "yes"):
                qs = qs.filter(is_published=True)
            elif str(is_published).lower() in ("false", "0", "no"):
                qs = qs.filter(is_published=False)
        else:
            qs = qs.filter(is_published=True)
        is_featured = self.request.query_params.get("is_featured")
        if is_featured is not None and str(is_featured).lower() in ("true", "1", "yes"):
            qs = qs.filter(is_featured=True)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        tag_slug = self.request.query_params.get("tag")
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        return qs.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return NewsListSerializer
        return NewsSerializer


class ReviewViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Отзывы на товары: list, retrieve, create.
    Создавать может любой (гость — name/email, авторизованный — user подставляется).
    Фильтр по product, is_approved (по умолчанию только одобренные).
    """

    permission_classes = (AllowAny,)
    pagination_class = ContentPagination

    def get_queryset(self):
        qs = (
            Review.objects.all()
            .select_related("user", "product")
            .order_by("-created_at")
        )
        product_id = self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)
        is_approved = self.request.query_params.get("is_approved")
        if is_approved is not None:
            if str(is_approved).lower() in ("true", "1", "yes"):
                qs = qs.filter(is_approved=True)
            elif str(is_approved).lower() in ("false", "0", "no"):
                qs = qs.filter(is_approved=False)
        else:
            qs = qs.filter(is_approved=True)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ReviewCreateSerializer
        return ReviewSerializer

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class PageGalleryListView(ListAPIView):
    """GET /api/v1/content/page-gallery/?placement=stores_hero|about_hero"""

    permission_classes = (AllowAny,)
    serializer_class = PageGalleryImageSerializer
    pagination_class = None
    throttle_classes = [AnonReadRateThrottle, UserReadRateThrottle]

    def get_queryset(self):
        placement = self.request.query_params.get("placement", "").strip()
        qs = PageGalleryImage.objects.filter(is_active=True)
        if placement:
            qs = qs.filter(placement=placement)
        return qs.order_by("sort_order", "id")
