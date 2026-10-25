"""
Статусы заказа в шлюзе Сбера (getOrderStatusExtended.orderStatus).

Источник: официальная документация ecom / ecom.yaml.
Одностадийный успех: orderStatus=2 (DEPOSITED) при actionCode=0.
"""

from __future__ import annotations

# Числовые статусы шлюза
ORDER_STATUS_REGISTERED = 0  # зарегистрирован, не оплачен
ORDER_STATUS_HELD = 1  # сумма захолдирована (preAuth)
ORDER_STATUS_DEPOSITED = 2  # списана / одностадийный успех
ORDER_STATUS_REVERSED = 3  # отмена
ORDER_STATUS_REFUNDED = 4  # возврат
ORDER_STATUS_ACS = 5  # ACS-авторизация инициирована
ORDER_STATUS_DECLINED = 6  # отказ

SUCCESS_ACTION_CODE = 0


def is_paid_one_stage(*, order_status: int | None, action_code: int | None) -> bool:
    """Успешная одностадийная оплата."""
    if order_status is None:
        return False
    if int(order_status) != ORDER_STATUS_DEPOSITED:
        return False
    if action_code is None:
        return False
    return int(action_code) == SUCCESS_ACTION_CODE


def is_terminal_failure(*, order_status: int | None) -> bool:
    """Отказ плательщика / ACS decline. REVERSED (3) обрабатывается отдельно."""
    if order_status is None:
        return False
    return int(order_status) == ORDER_STATUS_DECLINED
