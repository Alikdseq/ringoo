"""
Django Admin для возвратов.

Регистрация только при RETURNS_ENABLED=1. Модели и данные сохраняются всегда.
См. docs/audit/REFUNDS_TEMPORARILY_DISABLED.md
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin

from apps.returns.models import MoneyRefund, ReturnEvent, ReturnItem, ReturnRequest


if getattr(settings, "RETURNS_ENABLED", False):

    class ReturnItemInline(admin.TabularInline):
        model = ReturnItem
        extra = 0
        readonly_fields = (
            "order_item",
            "quantity",
            "unit_price",
            "line_refund_amount",
            "product_title",
            "color_label",
            "condition",
            "restocked_quantity",
        )
        can_delete = False

    class ReturnEventInline(admin.TabularInline):
        model = ReturnEvent
        extra = 0
        readonly_fields = ("from_status", "to_status", "message", "created_at", "actor")
        can_delete = False

    class MoneyRefundInline(admin.TabularInline):
        model = MoneyRefund
        extra = 0
        readonly_fields = (
            "amount",
            "status",
            "provider",
            "provider_refund_id",
            "idempotency_key",
            "error_message",
            "created_at",
        )
        can_delete = False

    @admin.register(ReturnRequest)
    class ReturnRequestAdmin(admin.ModelAdmin):
        list_display = (
            "number",
            "order",
            "status",
            "requested_refund_amount",
            "created_at",
        )
        list_filter = ("status", "ground", "demand")
        search_fields = ("number", "order__order_number")
        readonly_fields = ("number", "created_at", "updated_at")
        inlines = [ReturnItemInline, ReturnEventInline, MoneyRefundInline]
