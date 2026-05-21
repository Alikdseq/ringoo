"""
Админ-панель заказов (задача 1.5.6).
"""

import csv
from io import StringIO

from django.contrib import admin
from django.http import HttpResponse

from apps.audit.services import log_admin_action

from .models import ManagerRating, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "product_title", "product_sku", "quantity", "price", "item_total")
    readonly_fields = ("item_total",)
    raw_id_fields = ("product",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "full_name",
        "phone",
        "total_amount",
        "status",
        "delivery_type",
        "payment_type",
        "created_at",
    )
    list_filter = ("status", "payment_type", "delivery_type", "created_at")
    search_fields = ("phone", "full_name", "order_number")
    readonly_fields = (
        "id",
        "order_number",
        "created_at",
        "updated_at",
        "confirmation_email_sent_at",
    )
    inlines = [OrderItemInline]
    actions = ["action_set_status_confirmed", "action_export_csv"]

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = Order.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if change and old_status is not None and old_status != obj.status:
            log_admin_action(
                request,
                action="order_status_changed",
                model_name="orders.Order",
                object_id=str(obj.pk),
                object_repr=obj.order_number,
                changes={"status": {"old": old_status, "new": obj.status}},
            )

    @admin.action(description="Перевести в «Подтверждён»")
    def action_set_status_confirmed(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        updated = queryset.update(status=Order.STATUS_CONFIRMED)
        log_admin_action(
            request,
            action="order_bulk_status_confirmed",
            model_name="orders.Order",
            object_id=",".join(str(x) for x in ids[:50]),
            object_repr=f"{updated} заказов",
            changes={"status": Order.STATUS_CONFIRMED, "count": updated},
        )
        self.message_user(request, f"Обновлено заказов: {updated}.")

    @admin.action(description="Экспорт в CSV")
    def action_export_csv(self, request, queryset):
        log_admin_action(
            request,
            action="order_export_csv",
            model_name="orders.Order",
            object_id="",
            object_repr=f"export {queryset.count()} orders",
            changes={"count": queryset.count()},
        )
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "order_number",
                "full_name",
                "phone",
                "email",
                "status",
                "total_amount",
                "delivery_type",
                "payment_type",
                "created_at",
            ]
        )
        for order in queryset:
            writer.writerow(
                [
                    order.order_number,
                    order.full_name,
                    order.phone or "",
                    order.email or "",
                    order.status,
                    order.total_amount,
                    order.delivery_type,
                    order.payment_type,
                    order.created_at.isoformat() if order.created_at else "",
                ]
            )
        content = "\ufeff" + buf.getvalue()
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = "attachment; filename=orders.csv"
        return response


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_title", "product_sku", "quantity", "price", "item_total")
    list_filter = ("order__status",)
    search_fields = ("product_title", "product_sku", "order__order_number")
    raw_id_fields = ("order", "product")


@admin.register(ManagerRating)
class ManagerRatingAdmin(admin.ModelAdmin):
    list_display = ("order", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("order__order_number", "comment")
    raw_id_fields = ("order",)
    readonly_fields = ("created_at",)
