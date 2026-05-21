"""
Обезличивание заказов при удалении аккаунта (152-ФЗ).
"""

from django.utils import timezone

from apps.orders.models import Order

ANONYMIZED_FULL_NAME = "Удалён"
ANONYMIZED_PHONE = "00000000000"


def anonymize_orders_for_user(user) -> int:
    """Маскирует ПДн в заказах пользователя; возвращает число обновлённых строк."""
    now = timezone.now()
    return Order.objects.filter(user=user, anonymized_at__isnull=True).update(
        full_name=ANONYMIZED_FULL_NAME,
        phone=ANONYMIZED_PHONE,
        email=None,
        delivery_address={},
        comment=None,
        anonymized_at=now,
    )
