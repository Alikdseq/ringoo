"""
Общий throttling для API (задача 2.6.2).

Разные лимиты для read-only (каталог, магазины, контент) и остальных endpoints.
Отдельный лимит на создание заказа (защита от злоупотреблений).
"""

from django.core.exceptions import ImproperlyConfigured
from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class DynamicThrottleRatesMixin:
    """
    DRF кэширует SimpleRateThrottle.THROTTLE_RATES при импорте модуля; после
    django.test.override_settings(REST_FRAMEWORK=...) словарь в settings и класс
    расходятся. Читаем лимиты из api_settings при каждом создании throttle.
    """

    def get_rate(self):
        if not getattr(self, "scope", None):
            msg = "You must set either `.scope` or `.rate` for '%s' throttle" % (
                self.__class__.__name__,
            )
            raise ImproperlyConfigured(msg)
        try:
            return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
        except KeyError:
            msg = "No default throttle rate set for '%s' scope" % self.scope
            raise ImproperlyConfigured(msg)


class AnonReadRateThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """Повышенный лимит для анонимных запросов к read-only endpoints."""

    scope = "anon_read"


class UserReadRateThrottle(DynamicThrottleRatesMixin, UserRateThrottle):
    """Повышенный лимит для авторизованных запросов к read-only endpoints."""

    scope = "user_read"


class OrderCreateRateThrottle(DynamicThrottleRatesMixin, UserRateThrottle):
    """Ограничение частоты создания заказов: 20/час для авторизованных."""

    scope = "order_create"


class OrderCreateAnonRateThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """Ограничение частоты создания заказов гостями: 10/час по IP."""

    scope = "order_create_anon"


class OrderTrackAnonThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """Лимит запросов отслеживания заказа (номер + телефон)."""

    scope = "order_track"


class OrderRateAnonThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """Лимит отправки оценки заказа без авторизации."""

    scope = "order_rate"


class AuthLoginAnonThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """Лимит POST /auth/token/ (подбор пароля, DoS)."""

    scope = "auth_login"


class AuthRegisterAnonThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """Лимит POST /auth/register/ (массовая регистрация)."""

    scope = "auth_register"


class AuthRefreshAnonThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """Лимит POST /auth/token/refresh/ (злоупотребление refresh / DoS)."""

    scope = "auth_refresh"


class CartReadRateThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """GET корзины — гости и авторизованные (по IP / user)."""

    scope = "cart_read"


class CartWriteRateThrottle(DynamicThrottleRatesMixin, UserRateThrottle):
    """Мутации корзины для авторизованных."""

    scope = "cart_write"


class CartWriteAnonRateThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """Добавление в корзину гостем."""

    scope = "cart_write_anon"


class CrmCreateAnonThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """POST заявки «нет в наличии» (гость)."""

    scope = "crm_create"


class LegalAnalyticsAnonThrottle(DynamicThrottleRatesMixin, AnonRateThrottle):
    """POST согласия на cookie аналитики."""

    scope = "legal_analytics"

