"""
Админ-панель корзины (задача 1.4.6).
"""

from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ("product", "quantity", "price_at_add", "store")
    raw_id_fields = ("product", "store")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "items_count", "created_at", "updated_at")
    list_filter = ()
    search_fields = ("session_key", "user__phone")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [CartItemInline]

    @admin.display(description="Позиций")
    def items_count(self, obj):
        return obj.items.count()


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity", "price_at_add", "store", "updated_at")
    list_filter = ("store",)
    search_fields = ("product__title", "cart__session_key")
    raw_id_fields = ("cart", "product", "store")
