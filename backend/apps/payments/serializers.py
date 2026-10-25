from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order_id",
            "order_number",
            "provider",
            "status",
            "amount",
            "amount_kopecks",
            "currency",
            "merchant_order_number",
            "sber_order_id",
            "form_url",
            "sber_order_status",
            "action_code",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
