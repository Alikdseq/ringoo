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
    fields = (
        "product",
        "product_title",
        "product_sku",
        "onec_product_code",
        "onec_series_id",
        "quantity",
        "price",
        "item_total",
    )
    readonly_fields = ("item_total", "onec_product_code", "onec_series_id")
    raw_id_fields = ("product",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "full_name",
        "phone",
        "total_amount",
        "status",
        "onec_sync_status",
        "delivery_type",
        "payment_type",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_type",
        "delivery_type",
        "onec_sync_status",
        "created_at",
    )
    search_fields = (
        "phone",
        "full_name",
        "order_number",
        "onec_client_id",
        "onec_document_id",
    )
    readonly_fields = (
        "id",
        "order_number",
        "created_at",
        "updated_at",
        "confirmation_email_sent_at",
        "onec_client_id",
        "onec_warehouse_id",
        "onec_document_id",
        "onec_document_number",
        "onec_document_type",
        "onec_order_document_id",
        "onec_paid",
        "onec_posted",
        "onec_sync_status",
        "onec_last_error",
        "onec_synced_at",
        "onec_sync_attempts",
        "onec_payload_snapshot",
    )
    inlines = [OrderItemInline]
    actions = ["action_set_status_confirmed", "action_export_csv"]

    def save_model(self, request, obj, form, change):
        from django.contrib import messages

        from apps.orders.services import OrderCancelError
        from apps.orders.services.transitions import (
            OrderTransitionError,
            transition_order_status,
        )

        old_status = None
        if change and obj.pk:
            old_status = (
                Order.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
            )

        # INT-001/002: любая смена статуса — через FSM (cancel → release + 1С).
        if change and old_status is not None and obj.status != old_status:
            desired = obj.status
            obj.status = old_status
            super().save_model(request, obj, form, change)
            try:
                locked = transition_order_status(
                    obj,
                    desired,
                    reason="django_admin_status",
                    allow_paid_cancel=False,
                )
            except (OrderTransitionError, OrderCancelError) as exc:
                messages.error(request, getattr(exc, "message", str(exc)))
                return
            obj.status = locked.status
            log_admin_action(
                request,
                action="order_status_changed",
                model_name="orders.Order",
                object_id=str(obj.pk),
                object_repr=obj.order_number,
                changes={"status": {"old": old_status, "new": locked.status}},
            )
            return

        super().save_model(request, obj, form, change)

    @admin.action(description="Перевести в «Подтверждён»")
    def action_set_status_confirmed(self, request, queryset):
        from django.contrib import messages

        from apps.orders.services import OrderCancelError
        from apps.orders.services.transitions import (
            OrderTransitionError,
            transition_order_status,
        )

        ok = 0
        skipped = 0
        errors = []
        for order in queryset.iterator():
            try:
                locked = transition_order_status(
                    order,
                    Order.STATUS_CONFIRMED,
                    reason="django_admin_bulk_confirm",
                )
                if locked.status == Order.STATUS_CONFIRMED:
                    ok += 1
                else:
                    skipped += 1
            except (OrderTransitionError, OrderCancelError) as exc:
                skipped += 1
                if len(errors) < 5:
                    errors.append(f"{order.order_number}: {getattr(exc, 'message', exc)}")

        log_admin_action(
            request,
            action="order_bulk_status_confirmed",
            model_name="orders.Order",
            object_id="",
            object_repr=f"ok={ok} skipped={skipped}",
            changes={
                "status": Order.STATUS_CONFIRMED,
                "ok": ok,
                "skipped": skipped,
            },
        )
        msg = f"Подтверждено: {ok}. Пропущено/отклонено: {skipped}."
        if errors:
            msg += " " + "; ".join(errors)
        level = messages.WARNING if skipped else messages.SUCCESS
        self.message_user(request, msg, level=level)
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
