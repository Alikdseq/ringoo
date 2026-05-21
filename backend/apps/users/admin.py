"""
Админка для пользователей (задача 1.1.8).
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ConsentRecord, CustomUser, DeliveryAddress, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = True
    verbose_name_plural = "Профиль"
    fk_name = "user"


class DeliveryAddressInline(admin.TabularInline):
    model = DeliveryAddress
    extra = 0
    verbose_name_plural = "Адреса доставки"
    fk_name = "user"


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "phone",
        "email",
        "is_phone_verified",
        "is_email_verified",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_staff",
        "is_active",
        "is_phone_verified",
        "is_email_verified",
        "created_at",
    )
    search_fields = ("phone", "email", "username")
    ordering = ("-created_at",)
    inlines = (UserProfileInline, DeliveryAddressInline)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Личные данные", {"fields": ("email", "username")}),
        (
            "Верификация",
            {"fields": ("is_phone_verified", "is_email_verified")},
        ),
        (
            "Согласия (152-ФЗ)",
            {
                "fields": (
                    "privacy_policy_accepted_at",
                    "marketing_opt_in",
                    "marketing_opt_in_at",
                )
            },
        ),
        (
            "Права",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        ("Важные даты", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "email", "password1", "password2"),
            },
        ),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_login",
        "privacy_policy_accepted_at",
        "marketing_opt_in_at",
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "last_name", "first_name", "birth_date", "gender")
    list_filter = ("gender",)
    search_fields = ("user__phone", "first_name", "last_name", "middle_name")
    raw_id_fields = ("user",)


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = (
        "consent_type",
        "accepted_at",
        "user",
        "order",
        "policy_version",
        "ip_address",
    )
    list_filter = ("consent_type", "accepted_at", "policy_version")
    search_fields = ("user__phone", "ip_address", "user_agent")
    readonly_fields = (
        "id",
        "user",
        "order",
        "consent_type",
        "accepted_at",
        "ip_address",
        "policy_version",
        "user_agent",
    )
    raw_id_fields = ("user", "order")
    date_hierarchy = "accepted_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "city", "street", "house", "is_default", "created_at")
    list_filter = ("is_default", "city")
    search_fields = ("user__phone", "city", "street", "title")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
