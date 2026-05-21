"""Admin API: менеджеры магазинов — CRUD."""

from rest_framework import serializers, status
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.stores.models import Manager
from apps.stores.utils import generate_unique_manager_slug

from ..permissions import RINGOO_GROUP_STORES, admin_permissions


class ManagerAdminSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Manager
        fields = (
            "id",
            "name",
            "slug",
            "job_title",
            "bio",
            "photo",
            "photo_2",
            "photo_alt",
            "photo_2_alt",
            "store",
            "store_name",
            "is_active",
            "order",
        )
        read_only_fields = ("id", "store_name")
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }

    def validate_store(self, value):
        if value is None:
            raise serializers.ValidationError("Укажите магазин.")
        return value

    def create(self, validated_data):
        slug = (validated_data.get("slug") or "").strip()
        if not slug:
            validated_data["slug"] = generate_unique_manager_slug(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        slug = validated_data.get("slug")
        if slug is not None and not str(slug).strip():
            validated_data["slug"] = generate_unique_manager_slug(
                validated_data.get("name", instance.name),
                exclude_pk=instance.pk,
            )
        return super().update(instance, validated_data)


class ManagerAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    serializer_class = ManagerAdminSerializer
    pagination_class = PageNumberPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = Manager.objects.select_related("store").order_by("store__city", "order", "name")
        store_id = self.request.query_params.get("store", "").strip()
        if store_id:
            qs = qs.filter(store_id=store_id)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if str(is_active).lower() in ("true", "1", "yes"):
                qs = qs.filter(is_active=True)
            elif str(is_active).lower() in ("false", "0", "no"):
                qs = qs.filter(is_active=False)
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class ManagerAdminCreateView(CreateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    queryset = Manager.objects.all()
    serializer_class = ManagerAdminSerializer
    parser_classes = [MultiPartParser, FormParser]


class ManagerAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    queryset = Manager.objects.all()
    serializer_class = ManagerAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"
    parser_classes = [MultiPartParser, FormParser]

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
