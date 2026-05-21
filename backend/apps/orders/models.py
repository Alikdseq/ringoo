"""
Модели заказов: Order, OrderItem (задачи 1.5.1, 1.5.2).
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


def _generate_order_number():
    """Уникальный номер заказа: ORD-YYYYMMDD-6hex."""
    from django.utils import timezone
    import random
    date_part = timezone.now().strftime("%Y%m%d")
    suffix = f"{random.randint(0, 0xFFFFFF):06x}"
    return f"ORD-{date_part}-{suffix}"


class Order(models.Model):
    """Заказ."""

    DELIVERY_PICKUP = "pickup"
    DELIVERY_DELIVERY = "delivery"
    DELIVERY_CHOICES = [
        (DELIVERY_PICKUP, "Самовывоз"),
        (DELIVERY_DELIVERY, "Доставка"),
    ]

    PAYMENT_CASH = "cash"
    PAYMENT_CARD_ON_DELIVERY = "card_on_delivery"
    PAYMENT_BANK_TRANSFER = "bank_transfer"
    PAYMENT_ONLINE = "online"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Наличными"),
        (PAYMENT_CARD_ON_DELIVERY, "Картой при получении"),
        (PAYMENT_BANK_TRANSFER, "Банковский перевод"),
        (PAYMENT_ONLINE, "Онлайн"),
    ]

    STATUS_NEW = "new"
    STATUS_CONFIRMED = "confirmed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_NEW, "Новый"),
        (STATUS_CONFIRMED, "Подтверждён"),
        (STATUS_IN_PROGRESS, "В работе"),
        (STATUS_COMPLETED, "Выполнен"),
        (STATUS_CANCELLED, "Отменён"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Пользователь",
    )
    order_number = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        verbose_name="Номер заказа",
    )
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = models.CharField(max_length=50, verbose_name="Телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    delivery_type = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        verbose_name="Тип доставки",
    )
    delivery_address = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Адрес доставки",
        help_text="city, street, house, apartment, postal_code",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Магазин (самовывоз)",
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        verbose_name="Способ оплаты",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        verbose_name="Статус",
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма заказа",
    )
    delivery_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Стоимость доставки",
    )
    bonus_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Списано бонусов",
    )
    bonus_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Начислено бонусов",
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    consent_personal_data = models.BooleanField(
        default=False,
        verbose_name="Согласие на обработку персональных данных",
    )
    confirmation_email_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Письмо подтверждения заказа отправлено",
        help_text="Заполняется после успешной отправки; защита от повторной рассылки при retry Celery.",
    )
    anonymized_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Обезличен (удаление аккаунта)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "orders_order"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.order_number:
            while True:
                self.order_number = _generate_order_number()
                if not Order.objects.filter(order_number=self.order_number).exists():
                    break
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Позиция заказа."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Заказ",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="Товар",
    )
    product_title = models.CharField(
        max_length=255,
        verbose_name="Название на момент заказа",
    )
    product_sku = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Артикул",
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Цена на момент заказа",
    )
    item_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма по позиции",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "orders_orderitem"
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.product_title} × {self.quantity}"

    def save(self, *args, **kwargs):
        if self.price is not None and self.quantity is not None:
            self.item_total = self.price * self.quantity
        super().save(*args, **kwargs)


class ManagerRating(models.Model):
    """
    Оценка конкретного менеджера по заказу (ТЗ: рейтинг привязан к менеджеру и магазину).
    Один заказ — одна оценка; оценка указывает, какому менеджеру она поставлена.
    """

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="manager_rating",
        verbose_name="Заказ",
    )
    manager = models.ForeignKey(
        "stores.Manager",
        on_delete=models.PROTECT,
        related_name="ratings",
        verbose_name="Менеджер",
        null=True,
        blank=True,
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name="Оценка (1–5)",
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата оценки")

    class Meta:
        db_table = "orders_managerrating"
        verbose_name = "Оценка менеджера"
        verbose_name_plural = "Оценки менеджеров"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["rating"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["manager"]),
        ]

    def __str__(self):
        return f"{self.order.order_number} — {self.manager_id or '?'} — {self.rating}"
