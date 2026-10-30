"""
HTTP-клиент к сервисам 1С:УТ 11 (инструкция для разработчиков сайта).

Подтверждённые методы (публикация /razrab/hs/):
  GET  CatalogFolders/folders
  GET  CatalogProducts/products
  POST SiteRegistration/registrate
  POST SiteOrders/orders
  POST SiteOrders/orders/cancel

Секреты из django.conf.settings (fallback — env). Логи без Authorization/пароля.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from .url_utils import OneCBaseUrlError, normalize_onec_base_url

logger = logging.getLogger(__name__)

# Жёсткий потолок тела ответа 1С (защита от memory exhaustion).
_MAX_ONEC_RESPONSE_BYTES = 20 * 1024 * 1024


class _SameHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Запрещает redirect на другой host (снижение SSRF при скомпрометированном/ошибочном 1С)."""

    def __init__(self, allowed_netloc: str):
        super().__init__()
        self._allowed = (allowed_netloc or "").lower()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_host = (urlparse(newurl).netloc or "").lower()
        if not new_host or new_host != self._allowed:
            raise urllib.error.URLError(
                f"1C redirect to foreign host blocked ({new_host!r})"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class OneCClientError(Exception):
    """Ошибка клиента 1С (сеть, HTTP, разбор ответа)."""

    def __init__(self, message: str, *, status_code: int | None = None, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


@dataclass(frozen=True)
class OneCEndpoints:
    folders: str = "CatalogFolders/folders"
    products: str = "CatalogProducts/products"
    registration: str = "SiteRegistration/registrate"
    orders: str = "SiteOrders/orders"
    orders_cancel: str = "SiteOrders/orders/cancel"


def _settings_or_env(name: str, default: str = "") -> str:
    try:
        from django.conf import settings as dj_settings

        if hasattr(dj_settings, name):
            val = getattr(dj_settings, name)
            if val is not None and str(val).strip() != "":
                return str(val).strip()
    except Exception:  # noqa: BLE001 — settings могут быть не готовы
        pass
    return os.getenv(name, default).strip()


def _settings_flag(name: str) -> bool:
    try:
        from django.conf import settings as dj_settings

        if hasattr(dj_settings, name):
            return bool(getattr(dj_settings, name))
    except Exception:  # noqa: BLE001
        pass
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _settings_int(name: str, default: int) -> int:
    raw = _settings_or_env(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class OneCClient:
    """
    ONE_C_API_BASE_URL — напр. https://SERVER/razrab/hs (единая публикация)
    Учётные данные и флаги — из Django settings, затем env.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: int | None = None,
        username: str | None = None,
        password: str | None = None,
        enabled: bool | None = None,
        endpoints: OneCEndpoints | None = None,
        validate_base_url: bool = True,
    ):
        if base_url is not None:
            raw_base = base_url
        else:
            raw_base = _settings_or_env(
                "ONE_C_API_BASE_URL", "http://localhost/razrab/hs"
            )
        if validate_base_url and (raw_base or "").strip():
            try:
                self.base_url = normalize_onec_base_url(raw_base)
            except OneCBaseUrlError as exc:
                raise OneCClientError(str(exc), status_code=400) from exc
        else:
            self.base_url = (raw_base or "").rstrip("/") + "/"

        self.timeout = (
            timeout if timeout is not None else _settings_int("ONE_C_API_TIMEOUT", 60)
        )
        self.username = (
            username
            if username is not None
            else (
                _settings_or_env("ONE_C_LOGIN")
                or _settings_or_env("ONE_C_API_USER")
            )
        )
        self.password = (
            password
            if password is not None
            else (
                _settings_or_env("ONE_C_PASSWORD")
                or _settings_or_env("ONE_C_API_PASSWORD")
            )
        )
        self.enabled = (
            _settings_flag("ONE_C_API_ENABLED") if enabled is None else enabled
        )
        self.endpoints = endpoints or OneCEndpoints()

    def build_url(self, path: str) -> str:
        path = path.lstrip("/")
        if not self.base_url or self.base_url == "/":
            raise OneCClientError("ONE_C_API_BASE_URL не задан")
        return urljoin(self.base_url, path)

    def _auth_header(self) -> str | None:
        if not self.username:
            return None
        token = base64.b64encode(
            f"{self.username}:{self.password}".encode("utf-8")
        ).decode("ascii")
        return f"Basic {token}"

    def _http_open(self, request: urllib.request.Request):
        """
        Открывает HTTP с запретом redirect на чужой host.
        Вынесено методом для unit-тестов (patch OneCClient._http_open).
        """
        opener = urllib.request.build_opener(
            _SameHostRedirectHandler(urlparse(self.base_url).netloc)
        )
        return opener.open(request, timeout=self.timeout)

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        accept: str = "application/xml",
        expect_json: bool = False,
    ) -> tuple[int, bytes, str]:
        if not self.enabled:
            raise OneCClientError(
                "HTTP-клиент 1С выключен (ONE_C_API_ENABLED). "
                "Включайте только после подтверждения доступа к тестовому контуру."
            )
        url = self.build_url(path)
        data = None
        req_headers = {"Accept": accept}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req_headers["Content-Type"] = "application/json; charset=utf-8"
            req_headers["Accept"] = "application/json"

        request = urllib.request.Request(
            url, data=data, headers=req_headers, method=method.upper()
        )
        auth = self._auth_header()
        if auth:
            request.add_header("Authorization", auth)

        try:
            with self._http_open(request) as resp:  # nosec B310
                # Не читаем безлимитно
                raw = resp.read(_MAX_ONEC_RESPONSE_BYTES + 1)
                if len(raw) > _MAX_ONEC_RESPONSE_BYTES:
                    raise OneCClientError(
                        "Ответ 1С превышает допустимый размер",
                        status_code=int(getattr(resp, "status", 200) or 200),
                    )
                status = int(getattr(resp, "status", 200) or 200)
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = (exc.read(_MAX_ONEC_RESPONSE_BYTES + 1) or b"")[
                    :_MAX_ONEC_RESPONSE_BYTES
                ]
            except Exception:  # noqa: BLE001
                body = b""
            text = body.decode("utf-8", errors="replace")[:2000]
            logger.warning(
                "1C HTTP %s %s → %s (body_len=%s)",
                method.upper(),
                path,
                exc.code,
                len(body),
            )
            raise OneCClientError(
                self._public_http_message(exc.code, path),
                status_code=exc.code,
                body=text,
            ) from exc
        except TimeoutError as exc:
            logger.warning("1C timeout %s %s", method.upper(), path)
            raise OneCClientError(
                "Тайм-аут запроса к 1С",
                status_code=None,
                body="",
            ) from exc
        except urllib.error.URLError as exc:
            logger.warning("1C network error %s %s: %s", method.upper(), path, exc.reason)
            raise OneCClientError(f"Сеть недоступна для 1С: {exc.reason}") from exc

        if status >= 400:
            text = raw.decode("utf-8", errors="replace")[:2000]
            raise OneCClientError(
                self._public_http_message(status, path),
                status_code=status,
                body=text,
            )

        if expect_json and not raw.strip():
            raise OneCClientError("Пустой JSON-ответ от 1С", status_code=status)

        return status, raw, ctype or ("application/json" if expect_json else "application/xml")

    @staticmethod
    def _public_http_message(code: int, path: str) -> str:
        hints = {
            400: "Некорректный запрос к 1С",
            401: "Ошибка авторизации в 1С",
            403: "Недостаточно прав в 1С",
            404: "Сервис 1С не найден (проверьте URL и публикацию)",
            405: "Неподдерживаемый HTTP-метод для сервиса 1С",
            409: "Конфликт состояния в 1С",
            422: "Неверные ссылки или данные в 1С",
            500: "Внутренняя ошибка 1С",
        }
        base = hints.get(code, f"HTTP {code} от 1С")
        return f"{base} ({path})"

    def fetch_folders_xml(self) -> str:
        status, raw, _ = self.request(
            "GET",
            self.endpoints.folders,
            accept="application/xml",
        )
        text = raw.decode("utf-8", errors="replace")
        if not text.strip():
            raise OneCClientError(
                "Пустой XML категорий от 1С",
                status_code=status,
            )
        return text

    def fetch_products_xml(self) -> str:
        status, raw, _ = self.request(
            "GET",
            self.endpoints.products,
            accept="application/xml",
        )
        text = raw.decode("utf-8", errors="replace")
        if not text.strip():
            raise OneCClientError(
                "Пустой XML товаров от 1С",
                status_code=status,
            )
        return text

    def register_partner(
        self,
        *,
        last_name: str,
        first_name: str,
        phone: str,
        middle_name: str = "",
    ) -> dict[str, Any]:
        last_name = (last_name or "").strip()
        first_name = (first_name or "").strip()
        middle_name = (middle_name or "").strip()
        phone = (phone or "").strip()
        if not last_name or not first_name:
            raise OneCClientError(
                "Для регистрации в 1С нужны фамилия и имя",
                status_code=400,
            )
        payload = {
            "lastName": last_name,
            "firstName": first_name,
            "middleName": middle_name,
            "phone": phone,
        }
        status, raw, _ = self.request(
            "POST",
            self.endpoints.registration,
            payload=payload,
            accept="application/json",
            expect_json=True,
        )
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OneCClientError(
                "Ответ регистрации 1С не JSON",
                status_code=status,
                body=text[:2000],
            ) from exc
        if not isinstance(data, dict):
            raise OneCClientError(
                "Некорректная структура ответа регистрации 1С",
                status_code=status,
                body=text[:500],
            )
        if data.get("error"):
            raise OneCClientError(
                str(data.get("error")),
                status_code=status,
                body=text[:2000],
            )
        client_id = str(
            data.get("ClientId") or data.get("partnerId") or ""
        ).strip()
        if not client_id:
            raise OneCClientError(
                "В ответе 1С нет ClientId",
                status_code=status,
                body=text[:2000],
            )
        return {
            "ClientId": client_id,
            "partnerId": client_id,
            "created": bool(data.get("created", status == 201)),
            "http_status": status,
            "raw": data,
        }

    def create_or_update_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        status, raw, _ = self.request(
            "POST",
            self.endpoints.orders,
            payload=payload,
            accept="application/json",
            expect_json=True,
        )
        return self._parse_orders_json(status, raw, context="SiteOrders/orders")

    def cancel_order(
        self,
        *,
        order_id: str,
        paid: bool,
    ) -> dict[str, Any]:
        payload = {"orderId": str(order_id).strip(), "paid": bool(paid)}
        status, raw, _ = self.request(
            "POST",
            self.endpoints.orders_cancel,
            payload=payload,
            accept="application/json",
            expect_json=True,
        )
        return self._parse_orders_json(status, raw, context="SiteOrders/orders/cancel")

    def _parse_orders_json(
        self, status: int, raw: bytes, *, context: str
    ) -> dict[str, Any]:
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OneCClientError(
                f"Ответ {context} не JSON",
                status_code=status,
                body=text[:2000],
            ) from exc
        if not isinstance(data, dict):
            raise OneCClientError(
                f"Некорректная структура ответа {context}",
                status_code=status,
                body=text[:500],
            )
        if data.get("error"):
            raise OneCClientError(
                str(data.get("error")),
                status_code=status,
                body=text[:2000],
            )
        data = dict(data)
        data["http_status"] = status
        return data
