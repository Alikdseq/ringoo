"""
HttpOnly-куки с JWT: дублируют тело ответа token/register/refresh (см. JWT_COOKIE_ENABLED).
Снижает ущерб от XSS по сравнению с localStorage; при отключённой куке поведение как раньше.
"""

from __future__ import annotations

from django.conf import settings

AUTH_COOKIES_REQUEST_HEADER = "HTTP_X_AUTH_COOKIES"
AUTH_COOKIES_HEADER_VALUE = "1"


def client_uses_cookie_auth(request) -> bool:
    """
    Клиент в режиме HttpOnly JWT (не читает access/refresh из JSON).
    Заголовок X-Auth-Cookies: 1 или JWT_COOKIE_ENABLED без явного отказа.
    """
    if not getattr(settings, "JWT_COOKIE_ENABLED", True):
        return False
    raw = request.META.get(AUTH_COOKIES_REQUEST_HEADER, "")
    if str(raw).strip().lower() in ("1", "true", "yes"):
        return True
    return False


def strip_tokens_from_response_data(data: dict) -> dict:
    """Убрать access/refresh из тела ответа при cookie-режиме."""
    out = {**data}
    out.pop("access", None)
    out.pop("refresh", None)
    return out


def _access_max_age() -> int:
    return int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())


def _refresh_max_age() -> int:
    return int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())


def set_jwt_cookies(
    response, access_token: str, refresh_token: str | None = None
) -> None:
    if not getattr(settings, "JWT_COOKIE_ENABLED", True):
        return
    secure = getattr(settings, "JWT_COOKIE_SECURE", not settings.DEBUG)
    samesite = getattr(settings, "JWT_COOKIE_SAMESITE", "Lax")
    access_name = getattr(settings, "JWT_COOKIE_ACCESS_NAME", "ringoo_access")
    refresh_name = getattr(settings, "JWT_COOKIE_REFRESH_NAME", "ringoo_refresh")
    path = getattr(settings, "JWT_COOKIE_PATH", "/")

    response.set_cookie(
        key=access_name,
        value=access_token,
        max_age=_access_max_age(),
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=path,
    )
    if refresh_token:
        response.set_cookie(
            key=refresh_name,
            value=refresh_token,
            max_age=_refresh_max_age(),
            httponly=True,
            secure=secure,
            samesite=samesite,
            path=path,
        )


def clear_jwt_cookies(response) -> None:
    access_name = getattr(settings, "JWT_COOKIE_ACCESS_NAME", "ringoo_access")
    refresh_name = getattr(settings, "JWT_COOKIE_REFRESH_NAME", "ringoo_refresh")
    path = getattr(settings, "JWT_COOKIE_PATH", "/")
    for name in (access_name, refresh_name):
        response.delete_cookie(key=name, path=path)
