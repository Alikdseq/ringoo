"""
Сигналы корзины: связывание при авторизации (задача 1.4.5).
"""

from .services import merge_guest_cart_into_user


def merge_cart_on_login(sender, request, user, **kwargs):
    """При входе по сессии (например админка) объединить гостевую корзину с корзиной user."""
    if request and user:
        merge_guest_cart_into_user(request, user)
