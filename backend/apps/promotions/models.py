"""
Модели акций и промокодов (задачи 2.3.1, 2.3.2).
"""

import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Promotion(models.Model):
    """Акция: скидка на товары/категории в период дат."""

    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_CHOICES = [
        (DISCOUNT_PERCENT, "Процент"),
        (DISCOUNT_FIXED, "Фиксированная сумма"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    image = models.ImageField(
        upload_to="promotions/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Изображение",
    )
    discount_type = models.CharField(
        max_length=16,
        choices=DISCOUNT_CHOICES,
        verbose_name="Тип скидки",
    )
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Значение скидки",
    )
    start_date = models.DateTimeField(verbose_name="Начало")
    end_date = models.DateTimeField(verbose_name="Окончание")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    products = models.ManyToManyField(
        "products.Product",
        related_name="promotions",
        blank=True,
        verbose_name="Товары",
    )
    categories = models.ManyToManyField(
        "products.Category",
        related_name="promotions",
        blank=True,
        verbose_name="Категории",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "promotions_promotion"
        verbose_name = "Акция"
        verbose_name_plural = "Акции"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.title

    def is_valid(self):
        """Проверка: активна и текущее время в периоде [start_date, end_date]."""
        if not self.is_active:
            return False
        now = timezone.now()
        return self.start_date <= now <= self.end_date


class PromoCode(models.Model):
    """Промокод: скидка по коду с лимитом использований и мин. суммой заказа."""

    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_CHOICES = [
        (DISCOUNT_PERCENT, "Процент"),
        (DISCOUNT_FIXED, "Фиксированная сумма"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Код",
        help_text="Будет сохранён в верхнем регистре",
    )
    discount_type = models.CharField(
        max_length=16,
        choices=DISCOUNT_CHOICES,
        verbose_name="Тип скидки",
    )
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Значение скидки",
    )
    max_uses = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Макс. использований",
    )
    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Использовано",
    )
    min_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Мин. сумма заказа",
    )
    start_date = models.DateTimeField(verbose_name="Начало")
    end_date = models.DateTimeField(verbose_name="Окончание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "promotions_promocode"
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def is_valid(self):
        """Проверка: активен, в периоде дат и не исчерпан лимит использований."""
        if not self.is_active:
            return False
        now = timezone.now()
        if not (self.start_date <= now <= self.end_date):
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True
