"""
События безопасности для мониторинга (OWASP 4.7.2): без паролей и без сырого телефона в логах.
"""

from __future__ import annotations

import logging

from config.pii import mask_phone

from .services import get_client_ip, normalize_phone

logger = logging.getLogger("ringoo.security.auth")


def _mask_login_identifier(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return "[empty]"
    n = normalize_phone(s)
    if n:
        return mask_phone(n)
    return "[non-phone]"


def log_login_failed(request, login_raw: str, reason: str = "invalid_credentials") -> None:
    """Неудачная попытка входа по телефону/паролю (JWT token)."""
    ip = get_client_ip(request) or "unknown"
    logger.warning(
        "auth_login_failed reason=%s ip=%s identifier=%s",
        reason,
        ip,
        _mask_login_identifier(login_raw),
    )


def log_token_refresh_failed(request, reason: str = "invalid_token") -> None:
    """Невалидный или просроченный refresh (кука/тело)."""
    ip = get_client_ip(request) or "unknown"
    logger.warning("auth_refresh_failed reason=%s ip=%s", reason, ip)
