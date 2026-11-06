"""
SEC-006: криптостойкий guest access token для гостевых заказов.

В БД хранится только SHA-256 хеш. Plaintext выдаётся при создании заказа
или после подтверждённого восстановления (email OTP) и не логируется.

Номер заказа + телефон НЕ являются секретом и не дают приватный доступ.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger("ringoo.security")

PUBLIC_RECOVER_DETAIL = (
    "Если заказ найден и email совпадает с указанным при оформлении, "
    "мы отправили ссылку для восстановления доступа."
)


def guest_token_ttl_days() -> int:
    return int(getattr(settings, "ORDER_GUEST_ACCESS_TOKEN_TTL_DAYS", 90) or 90)


def recovery_ttl_seconds() -> int:
    return int(getattr(settings, "ORDER_GUEST_RECOVERY_TTL_SECONDS", 900) or 900)


def hash_guest_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_guest_access_token(order) -> str:
    """
    Генерирует новый токен, сохраняет хеш+expiry на заказе, возвращает plaintext.
    Вызывать только для гостевых заказов (user is None).
    """
    raw = secrets.token_urlsafe(32)
    order.guest_access_token_hash = hash_guest_token(raw)
    order.guest_access_token_expires_at = timezone.now() + timedelta(
        days=guest_token_ttl_days()
    )
    order.save(
        update_fields=[
            "guest_access_token_hash",
            "guest_access_token_expires_at",
            "updated_at",
        ]
    )
    return raw


def verify_guest_access_token(order, raw: str | None) -> bool:
    """Constant-time сравнение хеша; учитывает expiry."""
    if not raw or not str(raw).strip():
        return False
    stored = (getattr(order, "guest_access_token_hash", None) or "").strip()
    if not stored:
        return False
    expires = getattr(order, "guest_access_token_expires_at", None)
    if expires is not None and expires <= timezone.now():
        return False
    digest = hash_guest_token(str(raw).strip())
    return secrets.compare_digest(digest, stored)


def order_has_guest_token(order) -> bool:
    return bool((getattr(order, "guest_access_token_hash", None) or "").strip())


def extract_guest_token(request) -> str:
    """guest_token / access_token из body или query (без логирования значения)."""
    data = getattr(request, "data", None) or {}
    if hasattr(data, "get"):
        for key in ("guest_token", "access_token", "gat"):
            val = data.get(key)
            if val:
                return str(val).strip()
    params = getattr(request, "query_params", None) or {}
    for key in ("guest_token", "access_token", "gat"):
        val = params.get(key)
        if val:
            return str(val).strip()
    return ""


def guest_may_access_order(request, order, *, phone: str = "", order_number: str = "") -> bool:
    """
    Гостевой доступ только по валидному guest_token.

    phone/order_number принимаются для совместимости вызовов, но сами по себе
    доступ не дают (SEC-006 final: legacy phone+number закрыт).
    """
    del phone, order_number  # не используются как секрет
    if getattr(order, "user_id", None):
        # Гостевой токен не открывает заказы зарегистрированных пользователей
        return False
    raw = extract_guest_token(request)
    return verify_guest_access_token(order, raw)


def _recovery_cache_key(order_id) -> str:
    return f"guest_order_recover:{order_id}"


def _email_rate_key(email: str) -> str:
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]
    return f"guest_recover_email:{digest}"


def request_guest_access_recovery(*, order_number: str, email: str) -> None:
    """
    Инициирует восстановление: при совпадении гостевого заказа и email
    отправляет одноразовый recovery-токен. Не бросает различимых ошибок.
    """
    from apps.orders.models import Order

    order_number = (order_number or "").strip()
    email = (email or "").strip().lower()
    if not order_number or not email or "@" not in email:
        return

    # Лимит писем на email (не блокирует чужой аккаунт навсегда).
    er_key = _email_rate_key(email)
    sent = int(cache.get(er_key, 0) or 0)
    if sent >= int(getattr(settings, "ORDER_GUEST_RECOVERY_EMAIL_LIMIT", 3) or 3):
        logger.info("guest_recover_email_rate_limited")
        return

    order = (
        Order.objects.filter(order_number=order_number, user__isnull=True)
        .only("id", "order_number", "email", "user_id")
        .first()
    )
    if order is None:
        logger.info("guest_recover_unknown_order")
        return

    stored_email = (order.email or "").strip().lower()
    if not stored_email or stored_email != email:
        # Нет подтверждённого канала или несовпадение — без письма, тот же публичный ответ.
        logger.info("guest_recover_no_channel order_id=%s", order.pk)
        return

    raw = secrets.token_urlsafe(32)
    ttl = recovery_ttl_seconds()
    cache.set(
        _recovery_cache_key(order.pk),
        {"hash": hash_guest_token(raw), "order_number": order.order_number},
        timeout=ttl,
    )
    try:
        cache.incr(er_key)
    except ValueError:
        cache.set(er_key, 1, timeout=3600)

    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    link = (
        f"{base}/order-status"
        f"?recover=1&order_number={order.order_number}&token={raw}"
    )
    try:
        send_mail(
            subject="Восстановление доступа к заказу Ringo",
            message=(
                "Здравствуйте!\n\n"
                f"Запрошено восстановление доступа к заказу {order.order_number}.\n"
                "Откройте ссылку (действует ограниченное время):\n"
                f"{link}\n\n"
                "Если вы не запрашивали восстановление — проигнорируйте письмо."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ringoo.local"),
            recipient_list=[stored_email],
            fail_silently=True,
        )
    except Exception:
        logger.exception("guest_recover_email_failed order_id=%s", order.pk)
        cache.delete(_recovery_cache_key(order.pk))
        return
    logger.info("guest_recover_email_queued order_id=%s", order.pk)


def confirm_guest_access_recovery(*, order_number: str, recovery_token: str) -> str | None:
    """
    Проверяет одноразовый recovery-токен и выдаёт новый guest_access_token.
    Возвращает plaintext guest token или None.
    """
    from apps.orders.models import Order

    order_number = (order_number or "").strip()
    recovery_token = (recovery_token or "").strip()
    if not order_number or not recovery_token:
        return None

    order = Order.objects.filter(order_number=order_number, user__isnull=True).first()
    if order is None:
        return None

    cached = cache.get(_recovery_cache_key(order.pk))
    if not isinstance(cached, dict):
        return None
    stored_hash = str(cached.get("hash") or "")
    stored_number = str(cached.get("order_number") or "")
    if not stored_hash or stored_number != order.order_number:
        return None
    if not secrets.compare_digest(hash_guest_token(recovery_token), stored_hash):
        return None

    # Одноразовость: удаляем до выдачи постоянного токена.
    cache.delete(_recovery_cache_key(order.pk))
    return issue_guest_access_token(order)
