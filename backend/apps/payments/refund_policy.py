"""
Политика инициации денежных возвратов (YooKassa / Sber).

Входящие webhook/GET о возврате, сделанном вне приложения, не являются
инициацией и этим модулем не блокируются.
"""

from __future__ import annotations

from django.conf import settings


class RefundInitiationDisabled(Exception):
    """Попытка инициировать возврат при выключенной политике."""

    def __init__(
        self,
        message: str = (
            "Инициация денежных возвратов отключена. "
            "Возврат выполняется вручную в личном кабинете платёжного провайдера."
        ),
        *,
        code: str = "refund_initiation_disabled",
    ):
        self.message = message
        self.code = code
        super().__init__(message)


def refund_initiation_allowed() -> bool:
    """True только при явном PAYMENTS_REFUND_INITIATION_ENABLED=1|true|yes.

    В config.settings.production принудительно False независимо от env.
    """
    return bool(getattr(settings, "PAYMENTS_REFUND_INITIATION_ENABLED", False))


def assert_refund_initiation_allowed() -> None:
    if not refund_initiation_allowed():
        raise RefundInitiationDisabled()
