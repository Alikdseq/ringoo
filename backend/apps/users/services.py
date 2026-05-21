"""
Вспомогательные функции для пользователей (телефон и т.д.).
"""

import logging
import re

logger = logging.getLogger(__name__)


def normalize_phone(value: str) -> str | None:
    """
    Нормализация телефона: только цифры, для РФ — 11 цифр (начинается с 7).
    Невалидное значение — None.
    """
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return None
    if len(digits) == 10 and digits.startswith(("9", "8")):
        return "7" + digits
    if len(digits) == 11 and digits[0] == "8":
        return "7" + digits[1:]
    if len(digits) == 11 and digits[0] == "7":
        return digits
    return None


def is_valid_phone(value: str) -> bool:
    """Проверка: строка после нормализации — валидный российский номер (11 цифр, начинается с 7)."""
    normalized = normalize_phone(value)
    if not normalized:
        return False
    return len(normalized) == 11 and normalized[0] == "7"


def get_client_ip(request) -> str:
    """Клиентский IP (учёт X-Forwarded-For за прокси)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()[:45]
    addr = request.META.get("REMOTE_ADDR")
    return (addr or "").strip()[:45]


def record_successful_password_login(request, user) -> None:
    """
    Сохраняет IP входа; при смене IP отправляет предупреждение на email (если он задан).
    Не прерывает вход при ошибке почты.
    """
    from integrations.email_service import send_new_login_alert

    from .models import CustomUser

    ip = get_client_ip(request)
    row = CustomUser.objects.filter(pk=user.pk).only("last_login_ip", "email").first()
    if not row:
        return
    prev = (row.last_login_ip or "").strip() or None
    email = row.email
    CustomUser.objects.filter(pk=user.pk).update(last_login_ip=ip or None)
    if prev and ip and prev != ip and email:
        try:
            from config.pii import mask_phone

            send_new_login_alert(
                recipient_email=email,
                phone_display=mask_phone(getattr(user, "phone", "") or ""),
                new_ip=ip,
                previous_ip=prev,
            )
        except Exception:
            logger.exception("record_successful_password_login: notify failed for user %s", user.pk)
