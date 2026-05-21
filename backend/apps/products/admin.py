"""
Админ-панель каталога (задача 1.2.8).
"""

from django.contrib import admin

from .models import Category, Product, ProductColor, ProductImage, ProductSpec


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "parent", "is_active", "sort_order", "created_at")
    search_fields = ("title", "slug")
    list_filter = ("is_active", "parent")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at")
    list_editable = ("is_active", "sort_order")


class ProductColorInline(admin.TabularInline):
    model = ProductColor
    extra = 0
    fields = ("slug", "label", "hex", "price", "old_price", "sort_order", "is_active")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "color", "is_main", "alt_text", "sort_order")
    raw_id_fields = ("color",)


class ProductSpecInline(admin.TabularInline):
    model = ProductSpec
    extra = 0
    fields = ("name", "value", "sort_order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "category",
        "price",
        "old_price",
        "is_active",
        "is_featured",
        "created_at",
    )
    search_fields = ("title", "slug", "sku", "brand")
    list_filter = ("is_active", "is_featured", "category")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [ProductColorInline, ProductImageInline, ProductSpecInline]


@admin.register(ProductColor)
class ProductColorAdmin(admin.ModelAdmin):
    list_display = ("product", "label", "slug", "hex", "price", "old_price", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("label", "slug", "product__title")
    raw_id_fields = ("product",)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "image", "color", "is_main", "alt_text", "sort_order")
    list_filter = ("is_main",)
    search_fields = ("product__title", "alt_text")
    raw_id_fields = ("product", "color")


@admin.register(ProductSpec)
class ProductSpecAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "value", "sort_order")
    search_fields = ("name", "value", "product__title")
    raw_id_fields = ("product",)
