from django.contrib import admin

from .models import Promotion, PromoCode


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "discount_type", "discount_value", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "discount_type")
    search_fields = ("title",)
    filter_horizontal = ("products", "categories")


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "used_count", "max_uses", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "discount_type")
    search_fields = ("code",)
