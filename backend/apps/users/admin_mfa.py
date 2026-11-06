"""
Admin MFA (TOTP) for JWT / Admin API.

Password login never grants admin_mfa claim.
Staff must POST /auth/mfa/verify/ with a valid TOTP to receive tokens
with claim ADMIN_MFA_CLAIM=1. Admin API permissions require that claim
when ADMIN_OTP_ENABLED is true.

Does not log TOTP codes or secrets.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger("ringoo.security")

ADMIN_MFA_CLAIM = "admin_mfa"
ADMIN_MFA_CLAIM_VALUE = 1


def admin_otp_required() -> bool:
    return bool(getattr(settings, "ADMIN_OTP_ENABLED", False))


def user_has_confirmed_totp(user) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    try:
        from django_otp.plugins.otp_totp.models import TOTPDevice
    except Exception:
        return False
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def access_has_admin_mfa(token_payload: dict[str, Any] | None) -> bool:
    if not token_payload:
        return False
    return token_payload.get(ADMIN_MFA_CLAIM) == ADMIN_MFA_CLAIM_VALUE


def request_has_admin_mfa(request) -> bool:
    """True if access JWT carries verified admin MFA claim."""
    token = getattr(request, "auth", None)
    payload = None
    if token is not None:
        # UntypedToken / AccessToken behave like Mapping
        try:
            payload = dict(token)
        except Exception:
            payload = getattr(token, "payload", None)
    if isinstance(payload, dict) and access_has_admin_mfa(payload):
        return True
    return False


def issue_tokens_with_admin_mfa(user) -> tuple[str, str]:
    """Issue refresh+access with admin_mfa claim (after successful TOTP)."""
    refresh = RefreshToken.for_user(user)
    refresh[ADMIN_MFA_CLAIM] = ADMIN_MFA_CLAIM_VALUE
    access = refresh.access_token
    access[ADMIN_MFA_CLAIM] = ADMIN_MFA_CLAIM_VALUE
    return str(access), str(refresh)


def verify_totp_code(user, code: str) -> bool:
    """
    Verify TOTP against confirmed devices. Never log the code.
    """
    raw = (code or "").strip().replace(" ", "")
    if not raw.isdigit() or len(raw) < 6 or len(raw) > 8:
        return False
    try:
        from django_otp.plugins.otp_totp.models import TOTPDevice
    except Exception:
        logger.exception("django_otp TOTPDevice unavailable")
        return False
    devices = TOTPDevice.objects.filter(user=user, confirmed=True)
    for device in devices:
        try:
            if device.verify_token(raw):
                return True
        except Exception:
            logger.exception("TOTP verify_token failed for user_id=%s", getattr(user, "pk", None))
            return False
    return False


def staff_needs_mfa_step(user) -> bool:
    """Staff/superuser must complete MFA when OTP is enabled."""
    if not admin_otp_required():
        return False
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_staff or user.is_superuser)
