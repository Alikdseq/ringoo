"""
Интеграция django-axes с входом по телефону (credentials: phone / username) и JSON-ответом при lockout.
"""

from __future__ import annotations

from django.http import JsonResponse


def axes_get_username(request, credentials) -> str | None:
    """Идентификатор для учёта попыток: телефон или username из kwargs authenticate()."""
    if not credentials:
        return None
    raw = credentials.get("phone") or credentials.get("username")
    if raw is None:
        return None
    if isinstance(raw, str):
        s = raw.strip()
        return s or None
    return str(raw)


def axes_lockout_response(request, original_response=None, credentials=None, **kwargs):
    """DRF/JSON: 429 (axes: 3 аргумента или устаревший вызов (request, credentials))."""
    if credentials is None and isinstance(original_response, dict):
        credentials = original_response
        original_response = None
    return JsonResponse(
        {
            "detail": "Слишком много неудачных попыток входа. Повторите позже.",
        },
        status=429,
    )
