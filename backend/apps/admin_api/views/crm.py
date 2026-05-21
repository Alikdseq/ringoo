"""Admin API: CRM — заявки «Не нашли товар», смена статуса."""

from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.audit.services import log_admin_action
from apps.crm.models import MissingProductRequest

from ..permissions import RINGOO_GROUP_CRM, admin_permissions


class MissingProductRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissingProductRequest
        fields = (
            "id",
            "product_name",
            "contact_name",
            "contact_phone",
            "contact_email",
            "comment",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "product_name", "contact_name", "contact_phone", "contact_email", "comment", "created_at")


class MissingProductRequestAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissingProductRequest
        fields = ("status",)


class MissingProductRequestAdminListView(ListAPIView):
    """
    GET /api/v1/admin/crm/requests/ — список заявок.
    Параметры: ?status=new|processed|closed
    Доступ: staff.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_CRM)
    serializer_class = MissingProductRequestSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        qs = MissingProductRequest.objects.all().order_by("-created_at")
        st = (self.request.query_params.get("status") or "").strip()
        if st:
            qs = qs.filter(status=st)
        return qs


class MissingProductRequestAdminDetailView(RetrieveAPIView):
    """
    GET /api/v1/admin/crm/requests/{id}/ — детали заявки.
    Доступ: staff.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_CRM)
    queryset = MissingProductRequest.objects.all()
    serializer_class = MissingProductRequestSerializer
    lookup_url_kwarg = "pk"
    lookup_field = "pk"


class MissingProductRequestAdminUpdateView(UpdateAPIView):
    """
    PATCH /api/v1/admin/crm/requests/{id}/ — смена статуса.
    Доступ: staff.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_CRM)
    queryset = MissingProductRequest.objects.all()
    serializer_class = MissingProductRequestAdminUpdateSerializer
    http_method_names = ["patch"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def perform_update(self, serializer):
        instance = self.get_object()
        old_status = instance.status
        serializer.save()
        if old_status != serializer.instance.status:
            log_admin_action(
                self.request,
                action="update",
                model_name="MissingProductRequest",
                object_id=str(serializer.instance.pk),
                object_repr=str(serializer.instance),
                changes={"status": {"from": old_status, "to": serializer.instance.status}},
            )
