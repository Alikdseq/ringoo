"""
Celery tasks for users app.
"""

from __future__ import annotations

import logging

from django.conf import settings

from config.optional_task import shared_task

logger = logging.getLogger(__name__)


@shared_task
def test_celery_task():
    """
    Тестовая задача для проверки работы Celery.
    """
    return "Celery is working correctly!"


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def sync_user_partner_to_onec_task(self, user_id: str):
    """
    Асинхронная регистрация контрагента в 1С после signup.

    Не блокирует регистрацию на сайте. Реальный HTTP POST только если:
    ONE_C_API_ENABLED и ONE_C_SYNC_PARTNER_ON_REGISTER.
    """
    if not getattr(settings, "ONE_C_API_ENABLED", False):
        logger.info("onec partner sync skipped: ONE_C_API_ENABLED=false user=%s", user_id)
        return {"skipped": True, "reason": "api_disabled"}
    if not getattr(settings, "ONE_C_SYNC_PARTNER_ON_REGISTER", False):
        logger.info(
            "onec partner sync skipped: ONE_C_SYNC_PARTNER_ON_REGISTER=false user=%s",
            user_id,
        )
        return {"skipped": True, "reason": "flag_off"}

    from django.contrib.auth import get_user_model

    from integrations.onec.registration import (
        OneCRegistrationError,
        register_user_in_onec,
    )

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {"skipped": True, "reason": "user_missing"}

    try:
        result = register_user_in_onec(user)
        return {
            "skipped": result.skipped,
            "status": result.status,
            "partner_id": result.partner_id,
            "message": result.message,
        }
    except OneCRegistrationError as exc:
        logger.warning(
            "onec partner sync failed user=%s technical=%s",
            user_id,
            getattr(exc, "technical", str(exc)),
        )
        # Повтор только при сетевых/временных ошибках (pending_review уже защищён в сервисе)
        if "timeout" in (getattr(exc, "technical", "") or "").lower():
            raise self.retry(exc=exc)
        return {"ok": False, "error": exc.public_message}
    except Exception as exc:  # noqa: BLE001 — логируем и ретраим осторожно
        logger.exception("onec partner sync unexpected user=%s", user_id)
        raise self.retry(exc=exc)


def enqueue_partner_sync_after_register(user) -> None:
    """Ставит задачу после успешной регистрации; никогда не бросает наружу."""
    try:
        if not getattr(settings, "ONE_C_SYNC_PARTNER_ON_REGISTER", False):
            return
        if not getattr(settings, "ONE_C_API_ENABLED", False):
            logger.info(
                "partner sync deferred: API disabled after register user=%s",
                getattr(user, "pk", None),
            )
            return
        sync_user_partner_to_onec_task.delay(str(user.pk))
    except Exception:  # noqa: BLE001
        logger.exception("enqueue partner sync failed user=%s", getattr(user, "pk", None))
