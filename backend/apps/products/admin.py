"""
Админ-панель каталога (задача 1.2.8).
"""

from django.contrib import admin

from .models import Category, Product, ProductColor, ProductImage, ProductSpec
from .sync_models import OneCCatalogSyncLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "onec_code",
        "parent",
        "is_active",
        "sort_order",
        "created_at",
    )
    search_fields = ("title", "slug", "onec_code")
    list_filter = ("is_active", "parent")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "onec_code", "created_at", "updated_at")
    list_editable = ("is_active", "sort_order")

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj and getattr(obj, "onec_code", None):
            base.extend(["title", "slug", "parent"])
        seen = set()
        out = []
        for f in base:
            if f not in seen:
                seen.add(f)
                out.append(f)
        return out

    def save_model(self, request, obj, form, change):
        if change and getattr(obj, "onec_code", None):
            try:
                original = Category.objects.get(pk=obj.pk)
            except Category.DoesNotExist:
                original = None
            if original is not None:
                obj.title = original.title
                obj.slug = original.slug
                obj.parent_id = original.parent_id
                obj.onec_code = original.onec_code
        super().save_model(request, obj, form, change)


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
        "onec_code",
        "category",
        "price",
        "old_price",
        "is_active",
        "is_featured",
        "created_at",
    )
    search_fields = ("title", "slug", "sku", "brand", "onec_code")
    list_filter = ("is_active", "is_featured", "category")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [ProductColorInline, ProductImageInline, ProductSpecInline]

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj and getattr(obj, "onec_code", None):
            base.extend(
                [
                    "title",
                    "sku",
                    "price",
                    "old_price",
                    "category",
                    "onec_code",
                    "onec_type",
                ]
            )
        else:
            base.append("onec_code")
            base.append("onec_type")
        # unique preserve order
        seen = set()
        out = []
        for f in base:
            if f not in seen:
                seen.add(f)
                out.append(f)
        return out

    def save_model(self, request, obj, form, change):
        """Двойная защита: readonly UI + откат 1С-полей при обходе формы."""
        from .onec_protection import ONEC_MANAGED_PRODUCT_FIELDS, product_is_onec_managed

        if change and product_is_onec_managed(obj):
            try:
                original = Product.objects.get(pk=obj.pk)
            except Product.DoesNotExist:
                original = None
            if original is not None:
                for field in ONEC_MANAGED_PRODUCT_FIELDS:
                    if field == "category":
                        obj.category_id = original.category_id
                    else:
                        setattr(obj, field, getattr(original, field))
        super().save_model(request, obj, form, change)


@admin.register(ProductColor)
class ProductColorAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "label",
        "slug",
        "hex",
        "onec_code",
        "mapping_status",
        "price",
        "old_price",
        "sort_order",
        "is_active",
    )
    list_filter = ("is_active", "mapping_status")
    search_fields = ("label", "slug", "product__title", "onec_code")
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


@admin.register(OneCCatalogSyncLog)
class OneCCatalogSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "run_id",
        "sync_type",
        "status",
        "dry_run",
        "started_at",
        "finished_at",
        "products_updated",
        "errors_count",
    )
    list_filter = ("status", "dry_run", "sync_type")
    search_fields = ("run_id", "celery_task_id")
    readonly_fields = [f.name for f in OneCCatalogSyncLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
