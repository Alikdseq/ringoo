"""Admin API: Заказы — PATCH статуса и экспорт."""

import csv
from io import StringIO

from django.db.models import Q
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import serializers
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_admin_action
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer

from ..permissions import RINGOO_GROUP_ORDERS, admin_permissions


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

        # Допустимые переходы статусов
        allowed_transitions = {
            Order.STATUS_NEW: {Order.STATUS_CONFIRMED, Order.STATUS_CANCELLED},
            Order.STATUS_CONFIRMED: {
                Order.STATUS_IN_PROGRESS,
                Order.STATUS_CANCELLED,
            },
            Order.STATUS_IN_PROGRESS: {
                Order.STATUS_COMPLETED,
                Order.STATUS_CANCELLED,
            },
            Order.STATUS_COMPLETED: set(),
            Order.STATUS_CANCELLED: set(),
        }

        if value not in allowed_transitions.get(current, set()):
            raise serializers.ValidationError("Недопустимый переход статуса.")
        return value


class OrderAdminUpdateView(UpdateAPIView):
    """
    PATCH /api/v1/admin/orders/{id}/ — смена статуса заказа.
    Доступ только для staff.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)
    queryset = Order.objects.prefetch_related("items")
    http_method_names = ["patch"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def get_serializer_class(self):
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
        serializer.save()
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
        from django.utils.dateparse import parse_date
        from django.db.models import Q

        qs = Order.objects.all().order_by("-created_at")

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