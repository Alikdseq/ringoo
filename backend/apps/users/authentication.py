"""
JWT: Bearer и HttpOnly-куки.
Протухший/битый токен не должен ломать публичные эндпоинты (каталог, корзина) — трактуем как гостя.
"""

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class LenientJWTAuthentication(JWTAuthentication):
    """Bearer JWT: при InvalidToken/TokenError — гость, без 401 на AllowAny."""

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (InvalidToken, TokenError):
            return None


class JWTCookieAuthentication(JWTAuthentication):
    """Читает access-токен из куки, только когда Bearer в запросе отсутствует."""

    def authenticate(self, request):
        if self.get_header(request) is not None:
            return None
        name = getattr(settings, "JWT_COOKIE_ACCESS_NAME", "ringoo_access")
        raw = request.COOKIES.get(name)
        if not raw:
            return None
        try:
            validated = self.get_validated_token(raw)
            return self.get_user(validated), validated
        except (InvalidToken, TokenError):
            # Протухшая/битая кука — гость, публичные эндпоинты (каталог, корзина) не должны отдавать 401.
            return None
