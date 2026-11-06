"""Admin API: Заказы — список, детали, PATCH статуса и экспорт."""

import csv
from io import StringIO

from django.db.models import Q
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_admin_action
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from ..permissions import RINGOO_GROUP_ORDERS, admin_permissions


class OrderAdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _admin_orders_queryset(request):
    """Общие фильтры списка/экспорта заказов для admin_api."""
    qs = Order.objects.prefetch_related(
        "items", "manager_rating", "payments"
    ).order_by("-created_at")

    status_filter = (request.GET.get("status") or "").strip()
    if status_filter:
        qs = qs.filter(status=status_filter)

    delivery_type = (request.GET.get("delivery_type") or "").strip()
    if delivery_type:
        qs = qs.filter(delivery_type=delivery_type)

    payment_type = (request.GET.get("payment_type") or "").strip()
    if payment_type:
        qs = qs.filter(payment_type=payment_type)

    date_from = (request.GET.get("date_from") or "").strip()
    if date_from:
        d_from = parse_date(date_from)
        if d_from:
            qs = qs.filter(created_at__date__gte=d_from)

    date_to = (request.GET.get("date_to") or "").strip()
    if date_to:
        d_to = parse_date(date_to)
        if d_to:
            qs = qs.filter(created_at__date__lte=d_to)

    search = (request.GET.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(order_number__icontains=search)
            | Q(phone__icontains=search)
            | Q(full_name__icontains=search)
        )

    ordering = (request.GET.get("ordering") or "").strip()
    if ordering == "created_at":
        qs = qs.order_by("created_at")
    else:
        qs = qs.order_by("-created_at")
    return qs


class OrderAdminUpdateSerializer(serializers.ModelSerializer):
    """Только поля, разрешённые для изменения в админке: status."""

    class Meta:
        model = Order
        fields = ("status",)

    def validate_status(self, value):
        instance = getattr(self, "instance", None)
        if not instance:
            return value

        current = instance.status
        if value == current:
            return value

        from apps.orders.services.transitions import allowed_targets

        if value not in allowed_targets(current):
            raise serializers.ValidationError("Недопустимый переход статуса.")
        return value

class OrderAdminListView(ListAPIView):
    """
    GET /api/v1/admin/orders/ — список всех заказов (SEC-001: вместо staff-bypass
    на customer /api/v1/orders/).
    """

    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)
    serializer_class = OrderSerializer
    pagination_class = OrderAdminPagination

    def get_queryset(self):
        return _admin_orders_queryset(self.request)


class OrderAdminUpdateView(RetrieveUpdateAPIView):
    """
    GET /api/v1/admin/orders/{id}/ — детали заказа.
    PATCH /api/v1/admin/orders/{id}/ — смена статуса.
    SEC-003: переход в cancelled идёт через cancel_order_and_release_stock.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)
    queryset = Order.objects.prefetch_related("items", "payments", "manager_rating")
    http_method_names = ["get", "patch", "head", "options"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return OrderSerializer
        return OrderAdminUpdateSerializer

    def patch(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        old_status = instance.status
        serializer = OrderAdminUpdateSerializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data.get("status", old_status)

        from apps.orders.services import OrderCancelError
        from apps.orders.services.transitions import (
            OrderTransitionError,
            transition_order_status,
        )

        try:
            instance = transition_order_status(
                instance,
                new_status,
                reason="admin_api_status",
                allow_paid_cancel=False,
            )
        except (OrderTransitionError, OrderCancelError) as exc:
            return Response(
                {
                    "detail": getattr(exc, "message", str(exc)),
                    "code": getattr(exc, "code", "invalid_transition"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_admin_action(
            request,
            action="order_status_change",
            model_name="orders.Order",
            object_id=str(instance.pk),
            object_repr=instance.order_number,
            changes={"status": {"old": old_status, "new": instance.status}},
        )
        return Response(OrderSerializer(instance).data)


class OrderAdminExportView(APIView):
    """
    GET /api/v1/admin/orders/export/ — экспорт заказов в CSV по фильтрам.
    CSV легко открывается в Excel с русскими заголовками.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)

    def get(self, request):
        qs = _admin_orders_queryset(request)

        status_labels = {
            Order.STATUS_NEW: "Новый",
            Order.STATUS_CONFIRMED: "Подтверждён",
            Order.STATUS_IN_PROGRESS: "В работе",
            Order.STATUS_COMPLETED: "Выполнен",
            Order.STATUS_CANCELLED: "Отменён",
        }
        delivery_labels = {
            Order.DELIVERY_PICKUP: "Самовывоз",
            Order.DELIVERY_DELIVERY: "Доставка",
        }
        payment_labels = {
            Order.PAYMENT_CASH: "Наличными",
            Order.PAYMENT_CARD_ON_DELIVERY: "Картой при получении",
            Order.PAYMENT_BANK_TRANSFER: "Банковский перевод",
            Order.PAYMENT_ONLINE: "Онлайн",
        }

        header = [
            "Номер заказа",
            "ФИО",
            "Телефон",
            "Email",
            "Статус",
            "Сумма заказа, ₽",
            "Тип доставки",
            "Способ оплаты",
            "Списано бонусов, ₽",
            "Начислено бонусов, ₽",
            "Комментарий клиента",
            "Создан",
        ]

        buf = StringIO()
        writer = csv.writer(buf, delimiter=";")
        writer.writerow(header)

        for order in qs:
            created = (
                order.created_at.strftime("%d.%m.%Y %H:%M:%S")
                if order.created_at
                else ""
            )
            writer.writerow(
                [
                    order.order_number,
                    order.full_name,
                    order.phone or "",
                    order.email or "",
                    status_labels.get(order.status, order.status),
                    str(order.total_amount),
                    delivery_labels.get(order.delivery_type, order.delivery_type),
                    payment_labels.get(order.payment_type, order.payment_type),
                    str(order.bonus_used),
                    str(order.bonus_earned),
                    (order.comment or "")
                    .replace("\r", " ")
                    .replace("\n", " ")
                    .strip(),
                    created,
                ]
            )

        content = "\ufeff" + buf.getvalue()
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="orders.csv"'
        return response