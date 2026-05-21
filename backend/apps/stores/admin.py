"""
Админ-панель магазинов (задача 1.3.5).
"""

from django.contrib import admin

from .models import Manager, Store, Stock, StoreImage


class StoreImageInline(admin.TabularInline):
    model = StoreImage
    extra = 0
    fields = ("image", "alt_text", "sort_order", "is_active")


class ManagerInline(admin.TabularInline):
    model = Manager
    extra = 0
    fields = ("name", "slug", "job_title", "order", "is_active")
    readonly_fields = ("slug",)
    prepopulated_fields = {}


class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    fields = ("product", "quantity", "reserved_quantity")
    raw_id_fields = ("product",)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "city", "address", "is_active", "created_at")
    search_fields = ("name", "slug", "city", "address")
    list_filter = ("is_active", "city")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "name",
                    "slug",
                    "city",
                    "address",
                    "phone",
                    "email",
                    "latitude",
                    "longitude",
                    "working_hours",
                    "description",
                    "is_active",
                )
            },
        ),
        (
            "SEO",
            {"fields": ("meta_title", "meta_description")},
        ),
        (
            "Служебное",
            {"fields": ("created_at", "updated_at")},
        ),
    )
    inlines = [StoreImageInline, ManagerInline, StockInline]


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "store", "job_title", "order", "is_active")
    list_filter = ("is_active", "store")
    search_fields = ("name", "slug", "store__name")
    readonly_fields = ("slug",)
    raw_id_fields = ("store",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "store",
                    "name",
                    "slug",
                    "job_title",
                    "bio",
                    "order",
                    "is_active",
                )
            },
        ),
        (
            "Фото",
            {
                "fields": (
                    ("photo", "photo_alt"),
                    ("photo_2", "photo_2_alt"),
                )
            },
        ),
    )


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("product", "store", "quantity", "reserved_quantity", "available_quantity_display", "updated_at")
    list_filter = ("store",)
    search_fields = ("product__title", "store__name")
    raw_id_fields = ("product", "store")

    @admin.display(description="Доступно")
    def available_quantity_display(self, obj):
        return obj.available_quantity
