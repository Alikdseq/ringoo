"""
Админ-панель контента (задача 2.2.7).
"""

from django.contrib import admin

from .models import Article, News, PageGalleryImage, Review, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "category",
        "author",
        "is_published",
        "published_at",
        "views_count",
        "created_at",
    )
    list_filter = ("is_published", "category", "created_at")
    search_fields = ("title", "slug", "content", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)
    readonly_fields = ("id", "views_count", "created_at", "updated_at")
    filter_horizontal = ("tags",)
    date_hierarchy = "published_at"


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "category",
        "author",
        "is_published",
        "is_featured",
        "published_at",
        "views_count",
        "created_at",
    )
    list_filter = ("is_published", "is_featured", "category", "created_at")
    search_fields = ("title", "slug", "content", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)
    readonly_fields = ("id", "views_count", "created_at", "updated_at")
    filter_horizontal = ("tags",)
    date_hierarchy = "published_at"


@admin.register(PageGalleryImage)
class PageGalleryImageAdmin(admin.ModelAdmin):
    list_display = ("placement", "sort_order", "is_active", "created_at")
    list_filter = ("placement", "is_active")
    ordering = ("placement", "sort_order")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "user",
        "name",
        "rating",
        "is_approved",
        "is_verified_purchase",
        "created_at",
    )
    list_filter = ("is_approved", "is_verified_purchase", "rating", "created_at")
    search_fields = ("comment", "name", "email", "product__title")
    raw_id_fields = ("product", "user")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"
