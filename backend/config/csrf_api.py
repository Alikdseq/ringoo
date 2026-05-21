"""
CSRF для SPA с HttpOnly JWT-куками (double-submit cookie).

Bearer-only запросы не проверяются. Auth-эндпоинты (login/register/refresh/logout) exempt.
"""

from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.deprecation import MiddlewareMixin

# Префиксы API без CSRF (csrf_exempt views + публичные read)
_CSRF_EXEMPT_PREFIXES = (
    "/api/v1/auth/token/",
    "/api/v1/auth/register/",
    "/api/v1/auth/token/refresh/",
    "/api/v1/auth/logout/",
)

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _path_exempt(path: str) -> bool:
    if not path.startswith("/api/"):
        return True
    for prefix in _CSRF_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _has_jwt_cookie(request) -> bool:
    access = getattr(settings, "JWT_COOKIE_ACCESS_NAME", "ringoo_access")
    refresh = getattr(settings, "JWT_COOKIE_REFRESH_NAME", "ringoo_refresh")
    return bool(request.COOKIES.get(access) or request.COOKIES.get(refresh))


def _has_bearer_auth(request) -> bool:
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    return auth.startswith("Bearer ")


class JwtCookieCsrfMiddleware(MiddlewareMixin):
    """
    Для небезопасных методов к /api/: если есть JWT-кука и нет Bearer — требовать
    X-CSRFToken, совпадающий с csrftoken cookie.
    """

    def process_request(self, request):
        if request.method not in _UNSAFE_METHODS:
            return None
        if _path_exempt(request.path):
            return None
        if not getattr(settings, "JWT_COOKIE_ENABLED", True):
            return None
        if _has_bearer_auth(request):
            return None
        if not _has_jwt_cookie(request):
            return None

        cookie_token = request.COOKIES.get(settings.CSRF_COOKIE_NAME, "")
        header_token = request.META.get("HTTP_X_CSRFTOKEN", "")
        if cookie_token and header_token and cookie_token == header_token:
            return None

        return JsonResponse(
            {"detail": "CSRF Failed: missing or invalid X-CSRFToken."},
            status=403,
        )

    def process_response(self, request, response):
        if not request.path.startswith("/api/"):
            return response
        if not request.COOKIES.get(settings.CSRF_COOKIE_NAME):
            token = get_token(request)
            response.set_cookie(
                settings.CSRF_COOKIE_NAME,
                token,
                max_age=60 * 60 * 24 * 7,
                secure=getattr(settings, "CSRF_COOKIE_SECURE", False),
                httponly=False,
                samesite=getattr(settings, "CSRF_COOKIE_SAMESITE", "Lax"),
                path=getattr(settings, "CSRF_COOKIE_PATH", "/"),
            )
        return response
