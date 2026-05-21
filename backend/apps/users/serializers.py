"""
Сериализаторы для пользователя и профиля (задача 1.1.4, 1.1.5).
"""

from django.utils import timezone
from rest_framework import serializers

from .models import CustomUser, UserProfile, DeliveryAddress
from .services import is_valid_phone, normalize_phone


class DeliveryAddressSerializer(serializers.ModelSerializer):
    """Адрес доставки: список и создание/редактирование."""

    class Meta:
        model = DeliveryAddress
        fields = (
            "id",
            "title",
            "city",
            "street",
            "house",
            "apartment",
            "postal_code",
            "is_default",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class UserProfileSerializer(serializers.ModelSerializer):
    """Профиль пользователя: ФИО, аватар, дата рождения, пол."""

    class Meta:
        model = UserProfile
        fields = (
            "first_name",
            "last_name",
            "middle_name",
            "avatar",
            "birth_date",
            "gender",
        )
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    """Пользователь для API: без пароля, с вложенным профилем по необходимости."""

    profile = serializers.SerializerMethodField()

    def get_profile(self, obj):
        try:
            return UserProfileSerializer(obj.profile).data
        except UserProfile.DoesNotExist:
            return None

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "phone",
            "email",
            "is_phone_verified",
            "is_email_verified",
            "created_at",
            "updated_at",
            "privacy_policy_accepted_at",
            "marketing_opt_in",
            "marketing_opt_in_at",
            "profile",
        )
        read_only_fields = fields


class MarketingOptInSerializer(serializers.Serializer):
    """Обновление согласия на маркетинг (PATCH /auth/me/)."""

    marketing_opt_in = serializers.BooleanField(required=True)


class RegisterSerializer(serializers.Serializer):
    """Регистрация: телефон (логин), пароль, ФИО, согласия."""

    phone = serializers.CharField(max_length=20, trim_whitespace=True)
    password = serializers.CharField(max_length=128, min_length=8, write_only=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    middle_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    consent_personal_data = serializers.BooleanField(required=True)
    consent_offer = serializers.BooleanField(required=True)
    consent_marketing = serializers.BooleanField(required=False, default=False)

    def validate_consent_personal_data(self, value):
        if not value:
            raise serializers.ValidationError(
                "Необходимо согласие на обработку персональных данных.",
            )
        return value

    def validate_consent_offer(self, value):
        if not value:
            raise serializers.ValidationError("Необходимо принять условия публичной оферты.")
        return value

    def validate_phone(self, value):
        if not is_valid_phone(value):
            raise serializers.ValidationError("Некорректный номер телефона.")
        normalized = normalize_phone(value)
        if CustomUser.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError("Пользователь с таким телефоном уже зарегистрирован.")
        return normalized

    def create(self, validated_data):
        from .models import UserProfile

        validated_data.pop("consent_personal_data", None)
        validated_data.pop("consent_offer", None)
        consent_marketing = bool(validated_data.pop("consent_marketing", False))
        password = validated_data.pop("password")
        first_name = (validated_data.pop("first_name") or "").strip() or None
        last_name = (validated_data.pop("last_name") or "").strip() or None
        middle_name = (validated_data.pop("middle_name") or "").strip() or None
        now = timezone.now()
        user = CustomUser.objects.create_user(
            password=password,
            privacy_policy_accepted_at=now,
            marketing_opt_in=consent_marketing,
            marketing_opt_in_at=now if consent_marketing else None,
            **validated_data,
        )
        UserProfile.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )
        request = self.context.get("request")
        if request:
            from .consent import record_consent
            from .models import ConsentRecord

            record_consent(request, ConsentRecord.TYPE_PRIVACY, user=user)
            record_consent(request, ConsentRecord.TYPE_OFFER, user=user)
            if consent_marketing:
                record_consent(request, ConsentRecord.TYPE_MARKETING, user=user)
        return user
