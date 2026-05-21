"""
Запись согласий на обработку ПДн.
"""

from __future__ import annotations

from django.conf import settings

from .models import ConsentRecord


def get_client_ip(request) -> str | None:
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def get_user_agent(request) -> str:
    if not request:
        return ""
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]


def record_consent(
    request,
    consent_type: str,
    *,
    user=None,
    order=None,
) -> ConsentRecord:
    """Сохранить факт согласия с IP и версией политики."""
    return ConsentRecord.objects.create(
        user=user,
        order=order,
        consent_type=consent_type,
        ip_address=get_client_ip(request),
        policy_version=getattr(settings, "POLICY_VERSION", "2026-05-01"),
        user_agent=get_user_agent(request),
    )
