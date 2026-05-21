"""
Сериализаторы контента (задача 2.2.5).
"""

from rest_framework import serializers

from .models import Article, News, PageGalleryImage, Review, Tag


class TagSerializer(serializers.ModelSerializer):
    """Тег: id, name, slug."""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = fields


class ArticleSerializer(serializers.ModelSerializer):
    """Статья блога: все поля для списка/детали."""

    tags = TagSerializer(many=True, read_only=True)
    author_phone = serializers.SerializerMethodField()

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
            "author_phone",
            "category",
            "tags",
            "is_published",
            "published_at",
            "views_count",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_author_phone(self, obj):
        if obj.author_id and obj.author:
            return getattr(obj.author, "phone", None)
        return None


class ArticleListSerializer(serializers.ModelSerializer):
    """Статья для списка (без полного content)."""

    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "image",
            "category",
            "tags",
            "published_at",
            "views_count",
            "created_at",
        )
        read_only_fields = fields


class NewsSerializer(serializers.ModelSerializer):
    """Новость: все поля."""

    tags = TagSerializer(many=True, read_only=True)
    author_phone = serializers.SerializerMethodField()

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
            "author_phone",
            "category",
            "tags",
            "is_published",
            "is_featured",
            "published_at",
            "views_count",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_author_phone(self, obj):
        if obj.author_id and obj.author:
            return getattr(obj.author, "phone", None)
        return None


class NewsListSerializer(serializers.ModelSerializer):
    """Новость для списка."""

    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "image",
            "category",
            "tags",
            "is_featured",
            "published_at",
            "views_count",
            "created_at",
        )
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    """Отзыв: все поля (чтение)."""

    class Meta:
        model = Review
        fields = (
            "id",
            "product",
            "user",
            "name",
            "email",
            "rating",
            "comment",
            "is_approved",
            "is_verified_purchase",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "is_approved",
            "is_verified_purchase",
            "created_at",
            "updated_at",
        )


class PageGalleryImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = PageGalleryImage
        fields = ("id", "placement", "image", "alt_text", "sort_order")

    def get_image(self, obj):
        if not obj.image:
            return None
        from config.public_urls import absolute_media_url

        request = self.context.get("request")
        return absolute_media_url(request, obj.image.url)


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Создание отзыва (публичный или от пользователя)."""

    class Meta:
        model = Review
        fields = ("product", "name", "email", "rating", "comment")

    def validate_rating(self, value):
        if value not in (1, 2, 3, 4, 5):
            raise serializers.ValidationError("Оценка от 1 до 5.")
        return value

    def validate_comment(self, value):
        if not (value and value.strip()):
            raise serializers.ValidationError("Текст отзыва обязателен.")
        return value.strip()
