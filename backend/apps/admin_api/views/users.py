"""Admin API: Пользователи — список, детали, PATCH is_active/is_staff/groups."""

from django.contrib.auth.models import Group
from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.audit.services import log_admin_action
from apps.users.models import CustomUser, DeliveryAddress, UserProfile

from ..permissions import ALL_ADMIN_GROUPS, RINGOO_GROUP_USERS, admin_permissions


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            "id",
            "phone",
            "email",
            "is_active",
            "is_staff",
            "onec_partner_id",
            "onec_partner_status",
            "onec_partner_synced_at",
            "created_at",
        )
        read_only_fields = fields


class DeliveryAddressReadSerializer(serializers.ModelSerializer):
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
        )
        read_only_fields = fields


class UserProfileReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "first_name",
            "last_name",
            "middle_name",
            "birth_date",
            "gender",
        )
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    profile = UserProfileReadSerializer(read_only=True)
    delivery_addresses = DeliveryAddressReadSerializer(many=True, read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "phone",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "profile",
            "delivery_addresses",
            "onec_partner_id",
            "onec_partner_status",
            "onec_partner_synced_at",
            "onec_partner_last_error",
            "created_at",
        )
        read_only_fields = fields

    def get_groups(self, obj):
        return list(
            obj.groups.filter(name__in=ALL_ADMIN_GROUPS)
            .order_by("name")
            .values_list("name", flat=True)
        )


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    groups = serializers.ListField(
        child=serializers.ChoiceField(choices=[(g, g) for g in ALL_ADMIN_GROUPS]),
        required=False,
        write_only=True,
    )

    class Meta:
        model = CustomUser
        fields = ("is_active", "is_staff", "groups")

    def validate_is_staff(self, value):
        """Назначение staff — только суперпользователь."""
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        instance = getattr(self, "instance", None)
        current = bool(instance.is_staff) if instance is not None else False
        if value == current:
            return value
        if not user or not user.is_authenticated or not user.is_superuser:
            raise serializers.ValidationError(
                "Только суперпользователь может менять признак is_staff."
            )
        return value

    def validate_groups(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if value is None:
            return value
        if not user or not user.is_authenticated or not user.is_superuser:
            raise serializers.ValidationError(
                "Только суперпользователь может назначать группы ringoo_*."
            )
        unknown = [g for g in value if g not in ALL_ADMIN_GROUPS]
        if unknown:
            raise serializers.ValidationError(
                f"Неизвестные группы: {', '.join(unknown)}"
            )
        return value

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            ringoo_groups = Group.objects.filter(name__in=ALL_ADMIN_GROUPS)
            instance.groups.remove(*ringoo_groups)
            if groups:
                to_add = Group.objects.filter(name__in=groups)
                instance.groups.add(*to_add)
        return instance


class UserAdminListView(ListAPIView):
    """
    GET /api/v1/admin/users/ — список пользователей.
    Параметры: ?search=phone|email (поиск)
    """

    permission_classes = admin_permissions(RINGOO_GROUP_USERS)
    serializer_class = UserListSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        qs = CustomUser.objects.all().order_by("-created_at")
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(phone__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search)
            )
        return qs


class UserAdminDetailView(RetrieveAPIView):
    """GET /api/v1/admin/users/{id}/ — детали пользователя."""

    permission_classes = admin_permissions(RINGOO_GROUP_USERS)
    queryset = CustomUser.objects.prefetch_related(
        "delivery_addresses",
        "groups",
    ).select_related("profile")
    serializer_class = UserDetailSerializer
    lookup_url_kwarg = "pk"
    lookup_field = "pk"


class UserAdminUpdateView(UpdateAPIView):
    """
    PATCH /api/v1/admin/users/{id}/ — is_active, is_staff, groups.
    groups — только суперпользователь.
    Ответ — UserDetailSerializer (с groups).
    """

    permission_classes = admin_permissions(RINGOO_GROUP_USERS)
    queryset = CustomUser.objects.prefetch_related(
        "groups", "delivery_addresses"
    ).select_related("profile")
    serializer_class = UserAdminUpdateSerializer
    http_method_names = ["patch"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        before = {
            "is_active": instance.is_active,
            "is_staff": instance.is_staff,
            "groups": list(
                instance.groups.filter(name__in=ALL_ADMIN_GROUPS).values_list(
                    "name", flat=True
                )
            ),
        }
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = self.get_object()
        after = {
            "is_active": instance.is_active,
            "is_staff": instance.is_staff,
            "groups": list(
                instance.groups.filter(name__in=ALL_ADMIN_GROUPS).values_list(
                    "name", flat=True
                )
            ),
        }
        if before != after:
            log_admin_action(
                request,
                action="update",
                model_name="CustomUser",
                object_id=str(instance.pk),
                object_repr=str(instance.phone),
                changes={"user": {"from": before, "to": after}},
            )
        return Response(UserDetailSerializer(instance, context={"request": request}).data)

    def perform_update(self, serializer):
        serializer.save()
