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
from config.throttling import (
    PaymentCallbackAnonThrottle,
    PaymentPayAnonThrottle,
    PaymentPayUserThrottle,
    PaymentStatusAnonThrottle,
    PaymentStatusUserThrottle,
    YooKassaWebhookThrottle,
)

from .models import Payment
from .serializers import PaymentSerializer
from .services import (
    PaymentError,
    handle_sber_callback,
    initiate_online_payment,
    sync_payment_status,
)
from .yookassa_service import handle_yookassa_webhook

logger = logging.getLogger(__name__)

_ip_filter_off_logged = False


def yookassa_webhook_ip_allowed(request) -> bool:
    """
    Пустой allowlist не означает, что фильтр включён.
    Непустой список проверяет только REMOTE_ADDR, не сырой X-Forwarded-For.
    Включённый флаг при пустом списке отклоняет запрос.
    """
    global _ip_filter_off_logged
    raw = getattr(settings, "YOOKASSA_WEBHOOK_IP_ALLOWLIST", None) or []
    allowlist = [str(item).strip() for item in raw if str(item).strip()]
    enabled = bool(getattr(settings, "YOOKASSA_WEBHOOK_IP_FILTER_ENABLED", False))
    if not allowlist and not enabled:
        if not _ip_filter_off_logged:
            _ip_filter_off_logged = True
            logger.warning(
                "YooKassa webhook IP filter is off: allowlist is empty. "
                "Source IP is not checked. Paid status still requires a provider GET."
            )
        return True
    if not allowlist and enabled:
        logger.warning(
            "YooKassa webhook rejected: IP filter is enabled but allowlist is empty"
        )
        return False
    remote = (request.META.get("REMOTE_ADDR") or "").strip()
    if remote not in allowlist:
        logger.warning(
            "YooKassa webhook rejected by IP allowlist remote=%s",
            remote[:64],
        )
        return False
    return True


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
    """
    Владелец — по JWT (включая staff со своим заказом).
    Гость — только guest_access_token (SEC-006; phone+number недостаточно).
    SEC-001: is_staff не открывает чужие заказы на customer payment API.
    """
    if request.user.is_authenticated:
        if order.user_id == request.user.id:
            return True
    from apps.orders.guest_access import guest_may_access_order

    phone = (
        str(request.data.get("phone") or request.query_params.get("phone") or "")
        .strip()
    )
    order_number = (
        str(
            request.data.get("order_number")
            or request.query_params.get("order_number")
            or ""
        ).strip()
    )
    return guest_may_access_order(
        request, order, phone=phone, order_number=order_number
    )


class OrderPayView(APIView):
    """
    POST /api/v1/orders/{id}/pay/
    Создаёт платёж у активного провайдера (ЮKassa / Сбер), сумма из БД,
    возвращает form_url (= confirmation_url ЮKassa).
    Auth: владелец; гость — guest_token (SEC-006).
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
            result = initiate_online_payment(order)
        except PaymentError as exc:
            http = status.HTTP_400_BAD_REQUEST
            if exc.code == "already_paid":
                http = status.HTTP_409_CONFLICT
            elif exc.code in (
                "order_cancelled",
                "order_completed",
                "order_status",
                "not_online",
                "payment_blocked",
            ):
                http = status.HTTP_409_CONFLICT
            elif exc.code == "payment_status_unknown":
                http = status.HTTP_503_SERVICE_UNAVAILABLE
            elif exc.code in (
                "sber_register_failed",
                "yookassa_create_failed",
                "yookassa_unreachable",
            ):
                http = status.HTTP_502_BAD_GATEWAY
            elif exc.code in (
                "yookassa_misconfigured",
                "yookassa_test_key_required",
                "yookassa_live_key_required",
                "payments_disabled",
            ):
                http = status.HTTP_503_SERVICE_UNAVAILABLE
            return Response(
                {"code": exc.code, "detail": exc.message},
                status=http,
            )
        return Response(
            {
                "payment": PaymentSerializer(result.payment).data,
                "form_url": result.form_url,
                "confirmation_url": result.form_url,
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

        has_gateway_id = bool(
            (payment.provider == Payment.PROVIDER_YOOKASSA and payment.yookassa_payment_id)
            or (payment.provider == Payment.PROVIDER_SBER and payment.sber_order_id)
        )
        should_sync = (
            payment.status
            not in (
                Payment.STATUS_PAID,
                Payment.STATUS_EXPIRED,
                Payment.STATUS_REFUNDED,
                Payment.STATUS_REVERSED,
                Payment.STATUS_NEEDS_REVIEW,
                Payment.STATUS_FAILED,
            )
            and has_gateway_id
        )
        if should_sync and payment.last_status_checked_at:
            age = (timezone.now() - payment.last_status_checked_at).total_seconds()
            if age < self.BANK_SYNC_MIN_INTERVAL_SECONDS:
                should_sync = False

        if should_sync:
            try:
                payment = sync_payment_status(payment)
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


class YooKassaWebhookView(APIView):
    """
    POST /api/v1/payments/yookassa/webhook/
    SEC-007: throttle + size limit + валидация; paid только после re-fetch API.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [YooKassaWebhookThrottle]

    def post(self, request):
        if not yookassa_webhook_ip_allowed(request):
            return Response(
                {"detail": "forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        max_bytes = int(getattr(settings, "YOOKASSA_WEBHOOK_MAX_BODY_BYTES", 65536) or 65536)
        cl = request.META.get("CONTENT_LENGTH")
        try:
            if cl is not None and int(cl) > max_bytes:
                return Response(
                    {"detail": "payload too large"},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
        except (TypeError, ValueError):
            pass

        payload = request.data
        if not isinstance(payload, dict):
            return Response({"detail": "invalid"}, status=status.HTTP_400_BAD_REQUEST)

        # Грубая оценка сериализованного размера (защита от раздутых dict без CL)
        try:
            import json as _json

            if len(_json.dumps(payload, default=str)) > max_bytes:
                return Response(
                    {"detail": "payload too large"},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
        except Exception:
            return Response({"detail": "invalid"}, status=status.HTTP_400_BAD_REQUEST)

        event = str(payload.get("event") or "")
        obj = payload.get("object") if isinstance(payload.get("object"), dict) else {}
        logger.info(
            "YooKassa webhook event=%s payment_id=%s status=%s",
            event,
            obj.get("id"),
            obj.get("status"),
        )

        payment = handle_yookassa_webhook(payload)
        logger.info(
            "YooKassa webhook processed found=%s payment_id=%s",
            payment is not None,
            getattr(payment, "pk", None),
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)
