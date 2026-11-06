from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "merchant_order_number",
        "order",
        "provider",
        "status",
        "amount",
        "currency",
        "external_payment_id",
        "is_test",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "provider", "is_test", "created_at")
    search_fields = (
        "merchant_order_number",
        "sber_order_id",
        "yookassa_payment_id",
        "order__order_number",
        "error_message",
    )
    readonly_fields = (
        "id",
        "order",
        "provider",
        "status",
        "amount",
        "amount_kopecks",
        "currency",
        "merchant_order_number",
        "sber_order_id",
        "yookassa_payment_id",
        "is_test",
        "form_url",
        "sber_order_status",
        "action_code",
        "error_code",
        "register_response",
        "last_status_response",
        "paid_at",
        "callback_received_at",
        "last_status_checked_at",
        "created_at",
        "updated_at",
    )
    actions = ("mark_needs_review_ack",)

    @admin.display(description="ID платежа шлюза")
    def external_payment_id(self, obj: Payment) -> str:
        if obj.provider == Payment.PROVIDER_YOOKASSA:
            return obj.yookassa_payment_id or "—"
        return obj.sber_order_id or "—"

    @admin.action(description="Пометить needs_review как обработанный (failed)")
    def mark_needs_review_ack(self, request, queryset):
        updated = queryset.filter(status=Payment.STATUS_NEEDS_REVIEW).update(
            status=Payment.STATUS_FAILED,
            error_message="Сверка закрыта вручную в админке",
        )
        self.message_user(request, f"Обновлено: {updated}")
