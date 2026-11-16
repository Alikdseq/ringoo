"""
Админ-панель магазинов (задача 1.3.5).

ONEC-022: Stock в Django Admin — только просмотр.
Изменение quantity/reserved — через Admin API (stock_ops + StockMovement) или 1С.
"""

from django.contrib import admin

from .models import Manager, Stock, Store, StoreImage


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
    """Только просмотр остатков на карточке магазина (ONEC-022)."""

    model = Stock
    extra = 0
    can_delete = False
    fields = (
        "product",
        "onec_series_id",
        "onec_series_name",
        "quantity",
        "reserved_quantity",
        "updated_at",
    )
    readonly_fields = fields
    raw_id_fields = ("product",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "city",
        "address",
        "is_active",
        "is_warehouse",
        "onec_warehouse_id",
        "created_at",
    )
    search_fields = ("name", "slug", "city", "address", "onec_warehouse_id", "onec_warehouse_name")
    list_filter = ("is_active", "is_warehouse", "city")
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
            "1С / склад",
            {
                "fields": (
                    "onec_warehouse_id",
                    "onec_warehouse_name",
                    "is_warehouse",
                ),
                "description": (
                    "onec_warehouse_id обязателен для синхронизации заказов. "
                    "is_warehouse=True — метка «Склад»/Apple Room для клиентов; "
                    "точка участвует в наличии, корзине и заказе как обычный магазин."
                ),
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
    """
    ONEC-022: остатки только для просмотра.
    Ручная правка quantity — Admin API → apply_quantity_correction (с StockMovement).
    reserved_quantity — только через сервисы заказов (reserve/release).
    """

    list_display = (
        "product",
        "store",
        "onec_series_id",
        "quantity",
        "reserved_quantity",
        "available_quantity_display",
        "updated_at",
    )
    list_filter = ("store",)
    search_fields = ("product__title", "store__name", "onec_series_id")
    readonly_fields = (
        "id",
        "product",
        "store",
        "onec_series_id",
        "onec_series_name",
        "quantity",
        "reserved_quantity",
        "available_quantity_display",
        "updated_at",
    )
    fields = readonly_fields

    @admin.display(description="Доступно")
    def available_quantity_display(self, obj):
        return obj.available_quantity

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Не удаляем складские записи из Admin: история / резервы / sync 1С.
        return False

    def save_model(self, request, obj, form, change):
        # Readonly UI + no-op на случай обхода формы.
        return
