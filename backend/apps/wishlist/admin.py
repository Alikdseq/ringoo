from django.contrib import admin
from .models import WishlistItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__phone", "product__title", "product__sku")
    raw_id_fields = ("user", "product")
    readonly_fields = ("created_at",)
