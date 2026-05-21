"""
Логика корзины: связывание при авторизации (задача 1.4.5).
"""

from .models import Cart, CartItem


def merge_guest_cart_into_user(request, user):
    """
    При авторизации: найти корзину по session_key, объединить с корзиной user.
    - Если у гостя есть корзина по request.session.session_key — переносим товары
      в корзину пользователя (создаём её при необходимости).
    - Одинаковые (product, store) объединяем: quantity складываем.
    - Гостевую корзину удаляем.
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

    guest_cart.delete()
