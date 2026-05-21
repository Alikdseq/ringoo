"""Admin API: Пользователи — список, детали, PATCH is_active/is_staff."""

from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination

from apps.audit.services import log_admin_action
from apps.users.models import CustomUser, DeliveryAddress, UserProfile

from ..permissions import RINGOO_GROUP_USERS, admin_permissions


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            "id",
            "phone",
            "email",
            "is_active",
            "is_staff",
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

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "phone",
            "email",
            "is_active",
            "is_staff",
            "profile",
            "delivery_addresses",
            "created_at",
        )
        read_only_fields = fields


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("is_active", "is_staff")


class UserAdminListView(ListAPIView):
    """
    GET /api/v1/admin/users/ — список пользователей.
    Параметры: ?search=phone|email (поиск)
    Доступ: staff.
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
    """
    GET /api/v1/admin/users/{id}/ — детали пользователя.
    Доступ: staff.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_USERS)
    queryset = CustomUser.objects.prefetch_related(
        "delivery_addresses",
    ).select_related("profile")
    serializer_class = UserDetailSerializer
    lookup_url_kwarg = "pk"
    lookup_field = "pk"


class UserAdminUpdateView(UpdateAPIView):
    """
    PATCH /api/v1/admin/users/{id}/ — изменение is_active, is_staff.
    Доступ: staff.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_USERS)
    queryset = CustomUser.objects.all()
    serializer_class = UserAdminUpdateSerializer
    http_method_names = ["patch"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def perform_update(self, serializer):
        instance = self.get_object()
        before = {"is_active": instance.is_active, "is_staff": instance.is_staff}
        serializer.save()
        after = {
            "is_active": serializer.instance.is_active,
            "is_staff": serializer.instance.is_staff,
        }
        if before != after:
            log_admin_action(
                self.request,
                action="update",
                model_name="CustomUser",
                object_id=str(serializer.instance.pk),
                object_repr=str(serializer.instance.phone),
                changes={"user": {"from": before, "to": after}},
            )
