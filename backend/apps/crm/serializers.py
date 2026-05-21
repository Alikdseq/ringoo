"""
Сериализаторы CRM (заявки на отсутствующий товар).
"""

from rest_framework import serializers

from .models import MissingProductRequest


class MissingProductRequestCreateSerializer(serializers.ModelSerializer):
    """Создание заявки на отсутствующий товар."""

    consent_personal_data = serializers.BooleanField(write_only=True, required=True)
    consent_marketing = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = MissingProductRequest
        fields = (
            "id",
            "product_name",
            "contact_name",
            "contact_phone",
            "contact_email",
            "comment",
            "consent_personal_data",
            "consent_marketing",
        )
        read_only_fields = ("id",)

    def validate_consent_personal_data(self, value):
        if not value:
            raise serializers.ValidationError(
                "Необходимо согласие на обработку персональных данных."
            )
        return value

    def create(self, validated_data):
        consent_marketing = bool(validated_data.pop("consent_marketing", False))
        validated_data.pop("consent_personal_data", None)
        request = self.context.get("request")
        user = None
        if request and request.user.is_authenticated:
            user = request.user
            validated_data["user"] = user
        instance = super().create(validated_data)
        if request:
            from apps.users.consent import record_consent
            from apps.users.models import ConsentRecord

            lead_type = (
                ConsentRecord.TYPE_NEWSLETTER
                if (instance.product_name or "").startswith("Подписка")
                else ConsentRecord.TYPE_CRM_LEAD
            )
            record_consent(request, lead_type, user=user)
            if consent_marketing:
                record_consent(request, ConsentRecord.TYPE_MARKETING, user=user)
        return instance
