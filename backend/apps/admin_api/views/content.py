"""Admin API: Tag, Article, News — список и CRUD; Review moderation."""

from rest_framework import serializers
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status

from rest_framework.parsers import FormParser, MultiPartParser

from apps.content.models import Article, News, PageGalleryImage, Review, Tag

from ..permissions import RINGOO_GROUP_CONTENT, admin_permissions


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class ArticleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ("id", "title", "slug", "category", "is_published", "published_at", "created_at")


class ArticleAdminSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "content",
            "excerpt",
            "image",
            "author",
            "category",
            "tags",
            "is_published",
            "published_at",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")


class NewsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ("id", "title", "slug", "category", "is_published", "is_featured", "published_at", "created_at")


class NewsAdminSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "slug",
            "content",
            "excerpt",
            "image",
            "author",
            "category",
            "tags",
            "is_published",
            "is_featured",
            "published_at",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ("id", "product", "user", "name", "rating", "comment", "is_approved", "is_verified_purchase", "created_at")


class ReviewModerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ("is_approved",)


class TagAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
    pagination_class = None


class ArticleAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = Article.objects.all().order_by("-created_at")
    serializer_class = ArticleListSerializer
    pagination_class = PageNumberPagination


class ArticleAdminCreateView(CreateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = Article.objects.all()
    serializer_class = ArticleAdminSerializer

    def perform_create(self, serializer):
        user = self.request.user if self.request.user and self.request.user.is_authenticated else None
        serializer.save(author=user)


class ArticleAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = Article.objects.all()
    serializer_class = ArticleAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NewsAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = News.objects.all().order_by("-created_at")
    serializer_class = NewsListSerializer
    pagination_class = PageNumberPagination


class NewsAdminCreateView(CreateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = News.objects.all()
    serializer_class = NewsAdminSerializer

    def perform_create(self, serializer):
        user = self.request.user if self.request.user and self.request.user.is_authenticated else None
        serializer.save(author=user)


class NewsAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = News.objects.all()
    serializer_class = NewsAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = Review.objects.select_related("product", "user").order_by("-created_at")
    serializer_class = ReviewSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        qs = super().get_queryset()
        approved = self.request.query_params.get("is_approved")
        if approved is not None:
            if str(approved).lower() in ("true", "1", "yes"):
                qs = qs.filter(is_approved=True)
            elif str(approved).lower() in ("false", "0", "no"):
                qs = qs.filter(is_approved=False)
        return qs


class ReviewAdminUpdateView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = Review.objects.all()
    serializer_class = ReviewModerationSerializer
    http_method_names = ["patch"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"


class PageGalleryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageGalleryImage
        fields = (
            "id",
            "placement",
            "image",
            "alt_text",
            "sort_order",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class PageGalleryAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    serializer_class = PageGalleryAdminSerializer
    pagination_class = PageNumberPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = PageGalleryImage.objects.all().order_by("placement", "sort_order", "id")
        placement = self.request.query_params.get("placement", "").strip()
        if placement:
            qs = qs.filter(placement=placement)
        return qs


class PageGalleryAdminCreateView(CreateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = PageGalleryImage.objects.all()
    serializer_class = PageGalleryAdminSerializer
    parser_classes = [MultiPartParser, FormParser]


class PageGalleryAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CONTENT)
    queryset = PageGalleryImage.objects.all()
    serializer_class = PageGalleryAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"
    parser_classes = [MultiPartParser, FormParser]

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
