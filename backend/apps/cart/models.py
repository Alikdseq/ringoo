"""
Модели корзины: Cart, CartItem (задачи 1.4.1, 1.4.2).
"""

import uuid

from django.conf import settings
from django.db import models


class Cart(models.Model):
    """Корзина (пользователь или гость по session_key)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
        verbose_name="Пользователь",
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Ключ сессии (гости)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "cart_cart"
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["session_key"]),
        ]

    def __str__(self):
        if self.user_id:
            return f"Корзина {self.user}"
        return f"Корзина (гость {self.session_key[:8] if self.session_key else '?'}…)"

    def get_total(self):
        """Сумма по всем позициям (quantity * price_at_add)."""
        return sum(item.get_total() for item in self.items.all())

    @classmethod
    def get_or_create_cart(cls, request):
        """
        Получить или создать корзину для request.
        Авторизованный — по user, гость — по session.session_key.
        """
        if request.user.is_authenticated:
            cart, _ = cls.objects.get_or_create(
                user=request.user,
                defaults={"session_key": None},
            )
            return cart
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = cls.objects.get_or_create(
            session_key=session_key,
            user=None,
            defaults={},
        )
        return cart


class CartItem(models.Model):
    """Позиция в корзине."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Корзина",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="Товар",
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price_at_add = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Цена на момент добавления",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
        verbose_name="Магазин (самовывоз)",
    )
    color = models.ForeignKey(
        "products.ProductColor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
        verbose_name="Цвет",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "cart_cartitem"
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзины"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product", "store", "color"],
                name="cart_cartitem_cart_product_store_color_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["cart"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.product.title} × {self.quantity}"

    def get_total(self):
        """Сумма по позиции: quantity * price_at_add."""
        return self.quantity * self.price_at_add
