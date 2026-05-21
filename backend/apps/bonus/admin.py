"""
Админ-панель бонусной системы (задача 2.1.7).
"""

from django.contrib import admin

from .models import BonusAccount, BonusTransaction


class BonusTransactionInline(admin.TabularInline):
    model = BonusTransaction
    extra = 0
    fields = ("amount", "reason", "related_order", "description", "created_at")
    readonly_fields = ("created_at",)
    raw_id_fields = ("related_order",)
    ordering = ("-created_at",)
    show_change_link = True


@admin.register(BonusAccount)
class BonusAccountAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "balance",
        "total_earned",
        "total_spent",
        "updated_at",
    )
    search_fields = ("user__phone", "user__email")
    readonly_fields = ("id", "balance", "total_earned", "total_spent", "updated_at")
    inlines = [BonusTransactionInline]
    raw_id_fields = ("user",)

    def has_add_permission(self, request):
        return False  # счета создаются сигналом при создании пользователя


@admin.register(BonusTransaction)
class BonusTransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "amount", "reason", "related_order", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("account__user__phone", "description")
    readonly_fields = ("id", "created_at")
    raw_id_fields = ("account", "related_order")
    date_hierarchy = "created_at"
