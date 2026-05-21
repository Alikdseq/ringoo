"""Admin API: Магазины — список, создание, редактирование."""

from rest_framework import serializers, status
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.stores.models import Store, StoreImage
from config.public_urls import absolute_media_url

from ..permissions import RINGOO_GROUP_STORES, admin_permissions


class StoreAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = (
            "id",
            "name",
            "slug",
            "address",
            "city",
            "phone",
            "email",
            "latitude",
            "longitude",
            "working_hours",
            "description",
            "meta_title",
            "meta_description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class StoreAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    queryset = Store.objects.all().order_by("city", "name")
    serializer_class = StoreAdminSerializer
    pagination_class = PageNumberPagination


class StoreAdminCreateView(CreateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    queryset = Store.objects.all()
    serializer_class = StoreAdminSerializer


class StoreAdminUpdateView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    queryset = Store.objects.all()
    serializer_class = StoreAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StoreImageAdminSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StoreImage
        fields = (
            "id",
            "store",
            "image",
            "image_url",
            "alt_text",
            "sort_order",
            "is_active",
        )
        read_only_fields = ("id", "image_url", "store")

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return absolute_media_url(request, obj.image.url)


class StoreImageAdminListCreateView(CreateAPIView, ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    serializer_class = StoreImageAdminSerializer

    def get_queryset(self):
        store_id = self.kwargs.get("pk")
        return StoreImage.objects.filter(store_id=store_id).order_by("sort_order", "id")

    def perform_create(self, serializer):
        store_id = self.kwargs.get("pk")
        store = Store.objects.get(pk=store_id)
        serializer.save(store=store)


class StoreImageAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    queryset = StoreImage.objects.all()
    serializer_class = StoreImageAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"
