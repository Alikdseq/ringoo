"""
Custom middleware for security headers.
"""

from __future__ import annotations

# HTML: админка, DRF browsable API — inline script/style, без unsafe-eval.
_CSP_HTML_DJANGO = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

# Swagger UI / ReDoc требуют eval и инлайнов (сторонние бандлы на том же origin).
_CSP_API_DOCS = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


def _response_content_type(response) -> str:
    raw = response.get("Content-Type") or ""
    return raw.split(";")[0].strip().lower()


def _is_json_like_media_type(media_type: str) -> bool:
    if not media_type:
        return False
    if media_type == "application/json" or media_type.endswith("+json"):
        return True
    if media_type in ("application/problem+json", "application/vnd.api+json"):
        return True
    return False


class SecurityHeadersMiddleware:
    """
    Security headers: CSP зависит от типа ответа и пути.
    JSON API — без CSP (заголовок не несёт пользы для XHR/fetch).
    /api/docs, /api/redoc — ослабленная политика под UI документации.
    text/html — политика без unsafe-eval (админка, browsable API).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        # X-XSS-Protection не выставляем: устарел, в Chromium удалён; полагаемся на CSP и экранирование.
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        path = request.path or ""
        media_type = _response_content_type(response)

        if path.startswith("/api/docs") or path.startswith("/api/redoc"):
            response["Content-Security-Policy"] = _CSP_API_DOCS
            return response

        if _is_json_like_media_type(media_type):
            return response

        if "text/html" in (media_type or ""):
            response["Content-Security-Policy"] = _CSP_HTML_DJANGO

        return response
