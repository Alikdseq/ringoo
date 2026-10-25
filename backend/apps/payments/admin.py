from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "merchant_order_number",
        "order",
        "status",
        "amount",
        "sber_order_id",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "provider", "created_at")
    search_fields = (
        "merchant_order_number",
        "sber_order_id",
        "order__order_number",
        "error_message",
    )
    readonly_fields = (
        "id",
        "merchant_order_number",
        "sber_order_id",
        "form_url",
        "register_response",
        "last_status_response",
        "paid_at",
        "callback_received_at",
        "last_status_checked_at",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("order",)
    actions = ("mark_needs_review_ack",)

    @admin.action(description="Пометить needs_review как обработанный (failed)")
    def mark_needs_review_ack(self, request, queryset):
        updated = queryset.filter(status=Payment.STATUS_NEEDS_REVIEW).update(
            status=Payment.STATUS_FAILED,
            error_message="Сверка закрыта вручную в админке",
        )
        self.message_user(request, f"Обновлено: {updated}")
