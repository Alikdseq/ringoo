"""
Регистрация покупателя в 1С (POST SiteRegistration/registrate).

Только серверный слой. Не вызывается из браузера.
1С не поддерживает ключ идемпотентности — повторный POST после таймаута
запрещён автоматически; статус → pending_review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from .client import OneCClient, OneCClientError

logger = logging.getLogger(__name__)


class OneCRegistrationError(Exception):
    """Ошибка регистрации партнёра (без утечки секретов пользователю)."""

    def __init__(self, public_message: str, *, technical: str = ""):
        super().__init__(public_message)
        self.public_message = public_message
        self.technical = technical or public_message


@dataclass(frozen=True)
class RegistrationResult:
    partner_id: str | None
    status: str
    created: bool
    skipped: bool
    message: str


def _split_name(user) -> tuple[str, str, str]:
    profile = getattr(user, "profile", None)
    last_name = (getattr(profile, "last_name", None) or user.last_name or "").strip()
    first_name = (getattr(profile, "first_name", None) or user.first_name or "").strip()
    middle_name = (getattr(profile, "middle_name", None) or "").strip()
    return last_name, first_name, middle_name


def register_user_in_onec(
    user,
    *,
    client: OneCClient | None = None,
    force: bool = False,
) -> RegistrationResult:
    """
    Регистрирует пользователя в 1С и сохраняет partnerId.

    - Уже есть onec_partner_id → skip (повторный POST не выполняется).
    - pending_review без force → skip (нужна сверка с 1С).
    - select_for_update блокирует параллельные регистрации одного user.
    - Таймаут → pending_review, без автоповтора.
    """
    from apps.users.models import CustomUser

    with transaction.atomic():
        locked = (
            CustomUser.objects.select_for_update()
            .select_related("profile")
            .get(pk=user.pk)
        )

        if locked.onec_partner_id and not force:
            return RegistrationResult(
                partner_id=locked.onec_partner_id,
                status=locked.onec_partner_status or CustomUser.ONEC_PARTNER_SYNCED,
                created=False,
                skipped=True,
                message="partnerId уже сохранён",
            )

        if (
            locked.onec_partner_status == CustomUser.ONEC_PARTNER_PENDING_REVIEW
            and not force
        ):
            return RegistrationResult(
                partner_id=locked.onec_partner_id,
                status=CustomUser.ONEC_PARTNER_PENDING_REVIEW,
                created=False,
                skipped=True,
                message="Требуется сверка с 1С перед повторной отправкой",
            )

        last_name, first_name, middle_name = _split_name(locked)
        phone = (locked.phone or "").strip()
        if not last_name or not first_name:
            locked.onec_partner_status = CustomUser.ONEC_PARTNER_ERROR
            locked.onec_partner_last_error = "Нет фамилии или имени для 1С"
            locked.save(
                update_fields=[
                    "onec_partner_status",
                    "onec_partner_last_error",
                    "updated_at",
                ]
            )
            raise OneCRegistrationError(
                "Недостаточно данных для регистрации в 1С",
                technical="lastName/firstName empty",
            )

        api = client or OneCClient()
        try:
            result = api.register_partner(
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                phone=phone,
            )
        except OneCClientError as exc:
            # Таймаут / сеть без HTTP-кода → неоднозначный результат
            if exc.status_code is None:
                locked.onec_partner_status = CustomUser.ONEC_PARTNER_PENDING_REVIEW
                locked.onec_partner_last_error = str(exc)[:500]
                locked.save(
                    update_fields=[
                        "onec_partner_status",
                        "onec_partner_last_error",
                        "updated_at",
                    ]
                )
                logger.warning(
                    "1C registration indeterminate for user=%s: %s",
                    locked.pk,
                    exc,
                )
                return RegistrationResult(
                    partner_id=None,
                    status=CustomUser.ONEC_PARTNER_PENDING_REVIEW,
                    created=False,
                    skipped=False,
                    message="Неопределённый результат — требуется сверка с 1С",
                )

            locked.onec_partner_status = CustomUser.ONEC_PARTNER_ERROR
            locked.onec_partner_last_error = str(exc)[:500]
            locked.save(
                update_fields=[
                    "onec_partner_status",
                    "onec_partner_last_error",
                    "updated_at",
                ]
            )
            logger.warning(
                "1C registration failed user=%s status=%s",
                locked.pk,
                exc.status_code,
            )
            raise OneCRegistrationError(
                "Не удалось зарегистрировать покупателя в 1С",
                technical=str(exc),
            ) from exc

        partner_id = str(result.get("ClientId") or result.get("partnerId") or "").strip()
        locked.onec_partner_id = partner_id
        locked.onec_partner_status = CustomUser.ONEC_PARTNER_SYNCED
        locked.onec_partner_synced_at = timezone.now()
        locked.onec_partner_last_error = ""
        locked.save(
            update_fields=[
                "onec_partner_id",
                "onec_partner_status",
                "onec_partner_synced_at",
                "onec_partner_last_error",
                "updated_at",
            ]
        )
        return RegistrationResult(
            partner_id=partner_id,
            status=CustomUser.ONEC_PARTNER_SYNCED,
            created=bool(result.get("created")),
            skipped=False,
            message="ClientId сохранён",
        )


def public_registration_payload(
    last_name: str,
    first_name: str,
    phone: str,
    middle_name: str = "",
) -> dict[str, Any]:
    """Валидация полей до отправки (без HTTP)."""
    last_name = (last_name or "").strip()
    first_name = (first_name or "").strip()
    middle_name = (middle_name or "").strip()
    phone = (phone or "").strip()
    if not last_name or not first_name:
        raise OneCRegistrationError("Укажите фамилию и имя")
    return {
        "lastName": last_name,
        "firstName": first_name,
        "middleName": middle_name,
        "phone": phone,
    }
