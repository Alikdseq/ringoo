"""
Логика корзины: связывание при авторизации (задача 1.4.5).
"""

import logging

from django.db import transaction

from .models import Cart, CartItem

logger = logging.getLogger(__name__)


def merge_guest_cart_into_user(request, user):
    """
    При авторизации: найти корзину по session_key, объединить с корзиной user.
    - Если у гостя есть корзина по request.session.session_key — переносим товары
      в корзину пользователя (создаём её при необходимости).
    - Одинаковые (product, store) объединяем: quantity складываем.
    - Гостевую корзину удаляем.
    - checkout_cart_id неоплаченных online-заказов переназначаем на user_cart,
      иначе оплата после логина не сможет вычесть позиции из живой корзины.
    """
    if not request.session.session_key:
        return
    session_key = request.session.session_key
    guest_cart = Cart.objects.filter(
        session_key=session_key,
        user__isnull=True,
    ).prefetch_related("items").first()
    if not guest_cart:
        return

    with transaction.atomic():
        user_cart, _ = Cart.objects.get_or_create(
            user=user,
            defaults={"session_key": None},
        )

        for guest_item in guest_cart.items.all():
            item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=guest_item.product,
                store=guest_item.store,
                color=guest_item.color,
                defaults={
                    "quantity": guest_item.quantity,
                    "price_at_add": guest_item.price_at_add,
                },
            )
            if not created:
                item.quantity += guest_item.quantity
                item.save(update_fields=["quantity", "updated_at"])

        guest_cart_id = guest_cart.id
        # Перенос ссылок checkout с удаляемой гостевой корзины
        # (после paid checkout_cart_id уже None — такие заказы не затронем).
        from apps.orders.models import Order

        retargeted = Order.objects.filter(checkout_cart_id=guest_cart_id).update(
            checkout_cart_id=user_cart.id
        )
        if retargeted:
            logger.info(
                "checkout_cart_retargeted guest_cart=%s user_cart=%s orders=%s",
                guest_cart_id,
                user_cart.id,
                retargeted,
            )

        guest_cart.delete()
