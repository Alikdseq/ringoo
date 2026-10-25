"""
HTTP-клиент к ecom API Сбербанка (целевой шлюз).

Тест:  https://ecomtest.sberbank.ru
Бой:   https://epay.sberbank.ru  (не включать без явного подтверждения)

Пути:
  POST /ecomm/gw/partner/api/v1/register.do
  POST /ecomm/gw/partner/api/v1/getOrderStatusExtended.do

Секреты только из env. Пароль и Authorization не логируются.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class SberEcomError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        http_status: int | None = None,
        payload: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.http_status = http_status
        self.payload = payload or {}


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Боевой хост — только при явном SBER_ECOM_ALLOW_PRODUCTION=true
_SBER_PRODUCTION_HOST_MARKERS = ("epay.sberbank.ru",)


def _is_production_sber_base(base_url: str) -> bool:
    host = (base_url or "").lower()
    return any(marker in host for marker in _SBER_PRODUCTION_HOST_MARKERS)


class SberEcomClient:
    """
    SBER_ECOM_BASE_URL — без завершающего слэша (по умолчанию ecomtest)
    SBER_ECOM_USERNAME / SBER_ECOM_PASSWORD — логин *-api и пароль
    SBER_ECOM_TIMEOUT — секунды
    SBER_ECOM_ENABLED — без true сеть не вызывается
    SBER_ECOM_ALLOW_PRODUCTION — обязателен для https://epay.sberbank.ru
    """

    REGISTER_PATH = "/ecomm/gw/partner/api/v1/register.do"
    STATUS_PATH = "/ecomm/gw/partner/api/v1/getOrderStatusExtended.do"
    REVERSE_PATH = "/ecomm/gw/partner/api/v1/reverse.do"
    REFUND_PATH = "/ecomm/gw/partner/api/v1/refund.do"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int | None = None,
        enabled: bool | None = None,
        allow_production: bool | None = None,
    ):
        raw = (
            base_url
            if base_url is not None
            else os.getenv("SBER_ECOM_BASE_URL", "https://ecomtest.sberbank.ru")
        )
        self.base_url = (raw or "").rstrip("/")
        self.username = (
            username
            if username is not None
            else os.getenv("SBER_ECOM_USERNAME", "").strip()
        )
        self.password = (
            password
            if password is not None
            else os.getenv("SBER_ECOM_PASSWORD", "").strip()
        )
        self.timeout = (
            timeout if timeout is not None else _env_int("SBER_ECOM_TIMEOUT", 30)
        )
        self.enabled = (
            _env_flag("SBER_ECOM_ENABLED") if enabled is None else enabled
        )
        self.allow_production = (
            _env_flag("SBER_ECOM_ALLOW_PRODUCTION")
            if allow_production is None
            else allow_production
        )
        if _is_production_sber_base(self.base_url) and not self.allow_production:
            raise SberEcomError(
                "Боевой URL Сбера (epay) запрещён без SBER_ECOM_ALLOW_PRODUCTION=true. "
                "Для тестов используйте https://ecomtest.sberbank.ru"
            )

    def _url(self, path: str) -> str:
        if not self.base_url:
            raise SberEcomError("SBER_ECOM_BASE_URL не задан")
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise SberEcomError(
                "Клиент Сбера выключен (SBER_ECOM_ENABLED). "
                "Включайте только на тестовом контуре после выдачи доступов."
            )
        if _is_production_sber_base(self.base_url) and not self.allow_production:
            raise SberEcomError(
                "Боевой URL Сбера заблокирован (нет SBER_ECOM_ALLOW_PRODUCTION)"
            )
        if not self.username or not self.password:
            raise SberEcomError("Не заданы SBER_ECOM_USERNAME / SBER_ECOM_PASSWORD")

        # null-поля запрещены спецификацией — убираем None
        clean = {k: v for k, v in body.items() if v is not None}
        payload = {
            "userName": self.username,
            "password": self.password,
            **clean,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        url = self._url(path)
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:  # nosec B310
                raw = resp.read()
                http_status = int(getattr(resp, "status", 200) or 200)
        except urllib.error.HTTPError as exc:
            body_bytes = b""
            try:
                body_bytes = exc.read() or b""
            except Exception:  # noqa: BLE001
                body_bytes = b""
            text = body_bytes.decode("utf-8", errors="replace")[:2000]
            logger.warning(
                "Sber HTTP %s %s → %s body_len=%s",
                "POST",
                path,
                exc.code,
                len(body_bytes),
            )
            raise SberEcomError(
                f"HTTP {exc.code} от Сбера ({path})",
                http_status=exc.code,
                payload={"body": text},
            ) from exc
        except TimeoutError as exc:
            logger.warning("Sber timeout POST %s", path)
            raise SberEcomError("Тайм-аут запроса к Сберу", http_status=None) from exc
        except urllib.error.URLError as exc:
            logger.warning("Sber network error POST %s: %s", path, exc.reason)
            raise SberEcomError(f"Сеть недоступна для Сбера: {exc.reason}") from exc

        if not raw.strip():
            raise SberEcomError("Пустой ответ Сбера", http_status=http_status)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SberEcomError(
                "Ответ Сбера не JSON",
                http_status=http_status,
                payload={"body": raw.decode("utf-8", errors="replace")[:500]},
            ) from exc
        if not isinstance(parsed, dict):
            raise SberEcomError("Некорректная структура ответа Сбера", http_status=http_status)
        return parsed

    @staticmethod
    def _ensure_gateway_ok(data: dict[str, Any], *, context: str) -> None:
        code = str(data.get("errorCode", "0"))
        if code not in ("0", ""):
            msg = str(data.get("errorMessage") or data.get("error") or "Ошибка шлюза")
            raise SberEcomError(
                f"{context}: {msg}",
                error_code=code,
                payload=data,
            )

    def register_order(
        self,
        *,
        order_number: str,
        amount_kopecks: int,
        return_url: str,
        fail_url: str | None = None,
        description: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        currency: str = "643",
        session_timeout_secs: int | None = None,
        dynamic_callback_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Одностадийная регистрация. Возвращает orderId, formUrl при успехе.
        """
        body: dict[str, Any] = {
            "orderNumber": order_number,
            "amount": int(amount_kopecks),
            "currency": currency,
            "returnUrl": return_url,
            "language": "ru",
        }
        if fail_url:
            body["failUrl"] = fail_url
        if description:
            body["description"] = description[:99]
        if email:
            body["email"] = email
        if phone:
            body["phone"] = phone
        if session_timeout_secs is not None:
            body["sessionTimeoutSecs"] = int(session_timeout_secs)
        if dynamic_callback_url:
            body["dynamicCallbackUrl"] = dynamic_callback_url

        data = self._post(self.REGISTER_PATH, body)
        self._ensure_gateway_ok(data, context="register")
        order_id = str(data.get("orderId") or "").strip()
        form_url = str(data.get("formUrl") or "").strip()
        if not order_id or not form_url:
            raise SberEcomError(
                "В ответе register нет orderId/formUrl",
                payload=data,
            )
        return {
            "orderId": order_id,
            "formUrl": form_url,
            "errorCode": str(data.get("errorCode", "0")),
            "errorMessage": data.get("errorMessage"),
            "raw": data,
        }

    def get_order_status(
        self,
        *,
        order_id: str | None = None,
        order_number: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if order_id:
            body["orderId"] = order_id
        elif order_number:
            body["orderNumber"] = order_number
        else:
            raise SberEcomError("Нужен orderId или orderNumber")

        data = self._post(self.STATUS_PATH, body)
        self._ensure_gateway_ok(data, context="getOrderStatusExtended")
        return data

    def reverse_order(
        self,
        *,
        order_id: str,
        amount_kopecks: int | None = None,
    ) -> dict[str, Any]:
        """Отмена удержания / одностадийной оплаты в пределах банковского дня."""
        body: dict[str, Any] = {"orderId": order_id}
        if amount_kopecks is not None:
            body["amount"] = int(amount_kopecks)
        data = self._post(self.REVERSE_PATH, body)
        self._ensure_gateway_ok(data, context="reverse")
        return data

    def refund_order(
        self,
        *,
        order_id: str,
        amount_kopecks: int,
    ) -> dict[str, Any]:
        """Возврат средств (после взаиморасчётов). Готов к вызову из админки/ops."""
        body: dict[str, Any] = {
            "orderId": order_id,
            "amount": int(amount_kopecks),
        }
        data = self._post(self.REFUND_PATH, body)
        self._ensure_gateway_ok(data, context="refund")
        return data
