"""Admin API: Акции и промокоды — CRUD для списка, создания, редактирования и удаления."""

from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_admin_action
from apps.promotions.models import Promotion, PromoCode

from ..permissions import RINGOO_GROUP_CATALOG, admin_permissions


class PromotionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = (
            "id",
            "title",
            "description",
            "image",
            "discount_type",
            "discount_value",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PromoCodeAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = (
            "id",
            "code",
            "discount_type",
            "discount_value",
            "used_count",
            "max_uses",
            "min_order_amount",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "used_count", "created_at", "updated_at")


class PromotionAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = Promotion.objects.all().order_by("-start_date")
    serializer_class = PromotionAdminSerializer
    pagination_class = PageNumberPagination


class PromotionAdminCreateView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def post(self, request):
        serializer = PromotionAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promotion = serializer.save()
        log_admin_action(
            request,
            action="create",
            model_name="Promotion",
            object_id=str(promotion.pk),
            object_repr=promotion.title,
        )
        return Response(PromotionAdminSerializer(promotion).data, status=status.HTTP_201_CREATED)


class PromotionAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = Promotion.objects.all()
    serializer_class = PromotionAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        pk, title = str(instance.pk), instance.title
        instance.delete()
        log_admin_action(
            request,
            action="delete",
            model_name="Promotion",
            object_id=pk,
            object_repr=title,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PromoCodeAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = PromoCode.objects.all().order_by("-created_at")
    serializer_class = PromoCodeAdminSerializer
    pagination_class = PageNumberPagination


class PromoCodeAdminCreateView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def post(self, request):
        serializer = PromoCodeAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promocode = serializer.save()
        log_admin_action(
            request,
            action="create",
            model_name="PromoCode",
            object_id=str(promocode.pk),
            object_repr=promocode.code,
        )
        return Response(PromoCodeAdminSerializer(promocode).data, status=status.HTTP_201_CREATED)


class PromoCodeAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        pk, code = str(instance.pk), instance.code
        instance.delete()
        log_admin_action(
            request,
            action="delete",
            model_name="PromoCode",
            object_id=pk,
            object_repr=code,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
