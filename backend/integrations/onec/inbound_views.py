"""
HTTP endpoint: POST /api/v1/integrations/1c/orders/status/
"""

from __future__ import annotations

import hmac
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from integrations.onec.inbound import OneCInboundError, process_inbound_order_event

logger = logging.getLogger(__name__)


class OneCInboundThrottle(AnonRateThrottle):
    scope = "onec_inbound"


def _token_ok(request) -> bool:
    expected = (getattr(settings, "ONE_C_INCOMING_TOKEN", None) or "").strip()
    if not expected:
        return False
    got = (request.headers.get("X-OneC-Token") or "").strip()
    if not got:
        auth = (request.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
    if not got:
        return False
    return hmac.compare_digest(got.encode("utf-8"), expected.encode("utf-8"))


class OneCOrderStatusInboundView(APIView):
    """
    Входящие обновления статуса/оплаты от 1С.
    Авторизация: заголовок X-OneC-Token = ONE_C_INCOMING_TOKEN (env).
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [OneCInboundThrottle]

    def post(self, request):
        if not (getattr(settings, "ONE_C_INCOMING_TOKEN", None) or "").strip():
            logger.warning("ONE_C_INCOMING_TOKEN is not configured; inbound 1C rejected")
            return Response(
                {
                    "success": False,
                    "error": "inbound_disabled",
                    "message": "Inbound 1C integration is not configured",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not _token_ok(request):
            return Response(
                {
                    "success": False,
                    "error": "unauthorized",
                    "message": "Invalid or missing token",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not isinstance(request.data, dict):
            return Response(
                {
                    "success": False,
                    "error": "invalid_json",
                    "message": "JSON object required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            body = process_inbound_order_event(dict(request.data))
            return Response(body, status=status.HTTP_200_OK)
        except OneCInboundError as exc:
            return Response(
                {
                    "success": False,
                    "error": exc.code,
                    "message": exc.message,
                },
                status=exc.http_status,
            )
        except Exception:
            logger.exception("Unexpected error in 1C inbound handler")
            return Response(
                {
                    "success": False,
                    "error": "internal_error",
                    "message": "Internal error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
