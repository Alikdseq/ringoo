"""
HTTP-клиент ЮKassa API v3 (urllib, без requests).

Документация: https://yookassa.ru/developers/api
Авторизация: Basic Auth (shopId : secretKey).
Idempotence-Key обязателен для POST /payments и /refunds.
"""

from __future__ import annotations

import base64
import json
import logging
import ssl
import uuid
from decimal import Decimal
from typing import Any
from urllib import error, request

from django.conf import settings

logger = logging.getLogger(__name__)


class YooKassaError(Exception):
    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        payload: dict[str, Any] | None = None,
        code: str = "yookassa_error",
    ):
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.payload = payload or {}
        self.code = code


def _truthy(val: str | bool | None) -> bool:
    if isinstance(val, bool):
        return val
    return str(val or "").strip().lower() in ("1", "true", "yes", "on")


class YooKassaClient:
    """Минимальный клиент: create payment, get payment, create refund."""

    def __init__(
        self,
        *,
        shop_id: str | None = None,
        secret_key: str | None = None,
        api_url: str | None = None,
        enabled: bool | None = None,
        test_mode: bool | None = None,
        timeout: int | None = None,
    ):
        self.shop_id = (shop_id if shop_id is not None else getattr(settings, "YOOKASSA_SHOP_ID", "")).strip()
        self.secret_key = (
            secret_key if secret_key is not None else getattr(settings, "YOOKASSA_SECRET_KEY", "")
        ).strip()
        self.api_url = (
            api_url
            if api_url is not None
            else getattr(settings, "YOOKASSA_API_URL", "https://api.yookassa.ru/v3")
        ).rstrip("/")
        self.enabled = (
            bool(enabled)
            if enabled is not None
            else bool(getattr(settings, "YOOKASSA_ENABLED", False))
        )
        self.test_mode = (
            bool(test_mode)
            if test_mode is not None
            else bool(getattr(settings, "YOOKASSA_TEST_MODE", True))
        )
        self.timeout = int(
            timeout
            if timeout is not None
            else getattr(settings, "YOOKASSA_TIMEOUT", 30)
        )
        self._validate_config()

    def _validate_config(self) -> None:
        if not self.enabled:
            return
        missing = []
        if not self.shop_id:
            missing.append("YOOKASSA_SHOP_ID")
        if not self.secret_key:
            missing.append("YOOKASSA_SECRET_KEY")
        if missing:
            raise YooKassaError(
                "Онлайн-оплата не настроена (отсутствуют параметры конфигурации).",
                code="yookassa_misconfigured",
            )
        # Защита от случайного боя / теста
        key_is_test = self.secret_key.startswith("test_")
        if self.test_mode and not key_is_test:
            raise YooKassaError(
                "YOOKASSA_TEST_MODE=1 требует тестовый секретный ключ (test_…).",
                code="yookassa_test_key_required",
            )
        if not self.test_mode and key_is_test:
            raise YooKassaError(
                "Боевой режим не допускает тестовый ключ. Установите YOOKASSA_TEST_MODE=1 "
                "или укажите live-ключ.",
                code="yookassa_live_key_required",
            )
        if not self.api_url.startswith("https://api.yookassa.ru"):
            raise YooKassaError(
                "Недопустимый YOOKASSA_API_URL.",
                code="yookassa_bad_api_url",
            )

    def _auth_header(self) -> str:
        token = base64.b64encode(f"{self.shop_id}:{self.secret_key}".encode("utf-8")).decode(
            "ascii"
        )
        return f"Basic {token}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        idempotence_key: str | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise YooKassaError("ЮKassa отключена.", code="yookassa_disabled")

        url = f"{self.api_url}{path}"
        data = None
        headers = {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if method.upper() in ("POST", "PUT", "PATCH"):
            key = (idempotence_key or str(uuid.uuid4())).strip()
            headers["Idempotence-Key"] = key
            data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")

        req = request.Request(url, data=data, headers=headers, method=method.upper())
        ctx = ssl.create_default_context()
        try:
            with request.urlopen(req, timeout=self.timeout, context=ctx) as resp:
                raw = resp.read()
                status = getattr(resp, "status", 200)
        except error.HTTPError as exc:
            raw = exc.read() if exc.fp else b""
            payload: dict[str, Any] = {}
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                payload = {}
            # Не логируем Authorization / тело с возможными PII сверх description
            logger.warning(
                "YooKassa HTTP %s path=%s code=%s",
                exc.code,
                path,
                payload.get("code") or payload.get("type"),
            )
            desc = str(payload.get("description") or payload.get("code") or "Ошибка API ЮKassa")
            raise YooKassaError(
                desc[:512],
                http_status=exc.code,
                payload=_sanitize_yk_payload(payload),
                code="yookassa_http_error",
            ) from exc
        except error.URLError as exc:
            logger.warning("YooKassa unreachable path=%s: %s", path, type(exc.reason).__name__)
            raise YooKassaError(
                "Сервис оплаты временно недоступен.",
                code="yookassa_unreachable",
            ) from exc

        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise YooKassaError(
                "Некорректный ответ ЮKassa.",
                http_status=status,
                code="yookassa_bad_json",
            ) from exc

    def create_payment(
        self,
        *,
        amount: Decimal | str,
        return_url: str,
        description: str,
        metadata: dict[str, str],
        idempotence_key: str,
        currency: str = "RUB",
        capture: bool = True,
    ) -> dict[str, Any]:
        value = _format_amount(amount)
        body = {
            "amount": {"value": value, "currency": currency},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": capture,
            "description": (description or "")[:128],
            "metadata": metadata or {},
        }
        return self._request(
            "POST",
            "/payments",
            body=body,
            idempotence_key=idempotence_key,
        )

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        pid = str(payment_id or "").strip()
        if not pid:
            raise YooKassaError("Пустой payment_id", code="yookassa_bad_id")
        return self._request("GET", f"/payments/{pid}")

    def get_refund(self, refund_id: str) -> dict[str, Any]:
        """GET /refunds/{id} — источник истины для refund.succeeded (INT-004)."""
        rid = str(refund_id or "").strip()
        if not rid:
            raise YooKassaError("Пустой refund_id", code="yookassa_bad_refund_id")
        return self._request("GET", f"/refunds/{rid}")

    def create_refund(
        self,
        *,
        payment_id: str,
        amount: Decimal | str,
        currency: str = "RUB",
        idempotence_key: str | None = None,
    ) -> dict[str, Any]:
        body = {
            "payment_id": str(payment_id),
            "amount": {"value": _format_amount(amount), "currency": currency},
        }
        return self._request(
            "POST",
            "/refunds",
            body=body,
            idempotence_key=idempotence_key or str(uuid.uuid4()),
        )


def _format_amount(amount: Decimal | str) -> str:
    quantized = Decimal(str(amount)).quantize(Decimal("0.01"))
    return f"{quantized:.2f}"


def _sanitize_yk_payload(data: dict[str, Any]) -> dict[str, Any]:
    blocked = {"password", "secret", "authorization", "card", "payment_method"}
    out: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in blocked:
            continue
        out[k] = v
    return out
