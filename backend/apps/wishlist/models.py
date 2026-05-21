"""
Модель избранного (ТЗ EPIC 3: в ЛК — избранные товары).
"""

import uuid

from django.conf import settings
from django.db import models


class WishlistItem(models.Model):
    """Позиция избранного: пользователь + товар."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
        verbose_name="Пользователь",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="wishlist_items",
        verbose_name="Товар",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        db_table = "wishlist_wishlistitem"
        verbose_name = "Избранный товар"
        verbose_name_plural = "Избранные товары"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="wishlist_user_product_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.product.title}"
