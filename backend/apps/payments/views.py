"""
API оплаты: инициация, статус, callback Сбера.
"""

from __future__ import annotations

import logging
import secrets

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.views import _phone_matches_order
from config.throttling import (
    PaymentCallbackAnonThrottle,
    PaymentPayAnonThrottle,
    PaymentPayUserThrottle,
    PaymentStatusAnonThrottle,
    PaymentStatusUserThrottle,
)

from .models import Payment
from .serializers import PaymentSerializer
from .services import (
    PaymentError,
    handle_sber_callback,
    initiate_sber_payment,
    sync_payment_from_bank,
)

logger = logging.getLogger(__name__)


def _callback_token_required() -> bool:
    """
    True → пустой SBER_ECOM_CALLBACK_TOKEN отклоняет все callback.
    Явный SBER_ECOM_CALLBACK_TOKEN_REQUIRED; иначе fail-closed при DEBUG=False.
    """
    explicit = getattr(settings, "SBER_ECOM_CALLBACK_TOKEN_REQUIRED", None)
    if explicit is True:
        return True
    if explicit is False:
        return False
    return not bool(getattr(settings, "DEBUG", False))


def _callback_token_ok(request) -> bool:
    """
    Shared secret: ?token= или заголовок X-Sber-Callback-Token.
    Не заменяет getOrderStatusExtended; снижает abuse публичного URL.
    Токен никогда не логируется и не возвращается клиенту.
    """
    expected = str(getattr(settings, "SBER_ECOM_CALLBACK_TOKEN", "") or "").strip()
    if not expected:
        # Dev (DEBUG): callback без секрета допустим.
        # Staging/prod (DEBUG=False или REQUIRED=True): без секрета — отказ.
        return not _callback_token_required()
    provided = (
        str(request.query_params.get("token") or "").strip()
        or str(request.headers.get("X-Sber-Callback-Token") or "").strip()
    )
    if not provided or len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


def _can_access_order(request, order: Order) -> bool:
    if request.user.is_authenticated:
        if request.user.is_staff or order.user_id == request.user.id:
            return True
    phone = (
        str(request.data.get("phone") or request.query_params.get("phone") or "")
        .strip()
    )
    if phone and _phone_matches_order(order.phone, phone):
        return True
    return False


class OrderPayView(APIView):
    """
    POST /api/v1/orders/{id}/pay/
    Создаёт платёж в Сбере (сумма из БД) и возвращает form_url.
    Auth: владелец / staff; гость — phone в теле.
    """

    permission_classes = [AllowAny]

    def get_throttles(self):
        if self.request.user and self.request.user.is_authenticated:
            return [PaymentPayUserThrottle()]
        return [PaymentPayAnonThrottle()]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if not _can_access_order(request, order):
            return Response(
                {"detail": "Нет доступа к заказу."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            result = initiate_sber_payment(order)
        except PaymentError as exc:
            http = status.HTTP_400_BAD_REQUEST
            if exc.code == "already_paid":
                http = status.HTTP_409_CONFLICT
            elif exc.code == "sber_register_failed":
                http = status.HTTP_502_BAD_GATEWAY
            return Response(
                {"code": exc.code, "detail": exc.message},
                status=http,
            )
        return Response(
            {
                "payment": PaymentSerializer(result.payment).data,
                "form_url": result.form_url,
                "reused": result.reused,
            },
            status=status.HTTP_200_OK,
        )


class OrderPaymentStatusView(APIView):
    """
    GET /api/v1/orders/{id}/payment/
    Сверяет статус с банком (если есть незавершённый платёж) и отдаёт актуальные данные.
    """

    permission_classes = [AllowAny]
    # Debounce повторных getOrderStatusExtended при polling return-страницы.
    BANK_SYNC_MIN_INTERVAL_SECONDS = 5

    def get_throttles(self):
        if self.request.user and self.request.user.is_authenticated:
            return [PaymentStatusUserThrottle()]
        return [PaymentStatusAnonThrottle()]

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if not _can_access_order(request, order):
            return Response(
                {"detail": "Нет доступа к заказу."},
                status=status.HTTP_403_FORBIDDEN,
            )
        payment = (
            order.payments.exclude(status=Payment.STATUS_CREATED)
            .order_by("-created_at")
            .first()
        )
        if payment is None:
            payment = order.payments.order_by("-created_at").first()
        if payment is None:
            return Response(
                {"detail": "Платёж не создан.", "code": "no_payment"},
                status=status.HTTP_404_NOT_FOUND,
            )

        should_sync = (
            payment.status
            not in (
                Payment.STATUS_PAID,
                Payment.STATUS_EXPIRED,
                Payment.STATUS_REFUNDED,
                Payment.STATUS_REVERSED,
                Payment.STATUS_NEEDS_REVIEW,
            )
            and payment.sber_order_id
        )
        if should_sync and payment.last_status_checked_at:
            age = (timezone.now() - payment.last_status_checked_at).total_seconds()
            if age < self.BANK_SYNC_MIN_INTERVAL_SECONDS:
                should_sync = False

        if should_sync:
            try:
                payment = sync_payment_from_bank(payment)
            except PaymentError as exc:
                order.refresh_from_db()
                return Response(
                    {
                        "payment": PaymentSerializer(payment).data,
                        "order_status": order.status,
                        "sync_error": exc.message,
                        "code": exc.code,
                    },
                    status=status.HTTP_200_OK,
                )

        order.refresh_from_db()
        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "order_status": order.status,
                "order_payment_type": order.payment_type,
            }
        )


class SberCallbackView(APIView):
    """
    POST /api/v1/payments/sber/callback/
    Уведомление шлюза. Подлинность: сверка через getOrderStatusExtended
    (checksum в текущей OpenAPI не подтверждён как обязательный).
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PaymentCallbackAnonThrottle]

    def post(self, request):
        if not _callback_token_ok(request):
            logger.warning("Sber callback rejected: invalid or missing callback token")
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data
        if not isinstance(payload, dict):
            return Response({"detail": "invalid"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            "Sber callback operation=%s status=%s mdOrder=%s",
            payload.get("operation"),
            payload.get("status"),
            payload.get("mdOrder"),
        )
        payment = handle_sber_callback(payload)
        # Не отдаём found — иначе AllowAny-oracle по mdOrder/orderNumber.
        logger.info(
            "Sber callback accepted found=%s payment_id=%s",
            payment is not None,
            getattr(payment, "pk", None),
        )
        # Банк ожидает 200 при успешной приёмке; успешный HTTP ≠ paid.
        return Response({"ok": True}, status=status.HTTP_200_OK)
