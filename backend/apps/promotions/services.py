"""
Сервис применения промокодов (задача 2.3.3).
"""

from decimal import Decimal

from .models import PromoCode


def apply_promo_code(code, order_amount):
    """
    Валидация промокода и расчёт суммы скидки для заданной суммы заказа.

    - Валидация кода (нормализация, поиск).
    - Проверка дат, использований (is_valid()).
    - Проверка min_order_amount.
    - Расчёт скидки: percent — процент от суммы (не больше order_amount),
      fixed — фиксированная сумма (не больше order_amount).
    - Возврат суммы скидки или None при невалидном коде.
    """
    if not code or not str(code).strip():
        return None
    code = str(code).strip().upper()
    order_amount = Decimal(order_amount)
    if order_amount < 0:
        return None

    try:
        promo = PromoCode.objects.get(code=code)
    except PromoCode.DoesNotExist:
        return None

    if not promo.is_valid():
        return None

    if promo.min_order_amount is not None and order_amount < promo.min_order_amount:
        return None

    value = promo.discount_value
    if promo.discount_type == PromoCode.DISCOUNT_PERCENT:
        discount = (order_amount * value / Decimal("100")).quantize(Decimal("0.01"))
    else:
        discount = value

    if discount > order_amount:
        discount = order_amount
    if discount < 0:
        discount = Decimal("0")

    return discount.quantize(Decimal("0.01"))
