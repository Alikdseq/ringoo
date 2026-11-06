"""
Платёж через эквайринг (ЮKassa / Сбер ecom). Связан с Order; фискализация/1С — позже.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models


class Payment(models.Model):
    PROVIDER_SBER = "sber"
    PROVIDER_YOOKASSA = "yookassa"
    PROVIDER_CHOICES = [
        (PROVIDER_SBER, "Сбербанк ecom"),
        (PROVIDER_YOOKASSA, "ЮKassa"),
    ]

    STATUS_CREATED = "created"
    STATUS_REGISTERED = "registered"
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUS_REVERSED = "reversed"
    STATUS_REFUNDED = "refunded"
    STATUS_NEEDS_REVIEW = "needs_review"
    STATUS_CHOICES = [
        (STATUS_CREATED, "Создан"),
        (STATUS_REGISTERED, "Зарегистрирован в банке"),
        (STATUS_PENDING, "Ожидает оплаты"),
        (STATUS_PAID, "Оплачен"),
        (STATUS_FAILED, "Ошибка / отказ"),
        (STATUS_EXPIRED, "Истёк"),
        (STATUS_REVERSED, "Отменён (reverse)"),
        (STATUS_REFUNDED, "Возврат"),
        (STATUS_NEEDS_REVIEW, "Требует сверки"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Заказ",
    )
    provider = models.CharField(
        max_length=32,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_SBER,
        verbose_name="Провайдер",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        db_index=True,
        verbose_name="Статус платежа",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма (руб.)",
    )
    amount_kopecks = models.PositiveBigIntegerField(
        verbose_name="Сумма (копейки)",
    )
    currency = models.CharField(max_length=3, default="643", verbose_name="Валюта ISO")
    # orderNumber, уходящий в Сбер (уникален в рамках мерчанта)
    merchant_order_number = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        verbose_name="Номер заказа для Сбера",
    )
    sber_order_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        verbose_name="orderId Сбера",
    )
    yookassa_payment_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        verbose_name="payment_id ЮKassa",
    )
    yookassa_refund_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        verbose_name="refund_id ЮKassa",
        help_text="Последний подтверждённый полный возврат (INT-004)",
    )
    refunded_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Сумма возврата (руб.)",
    )
    refunded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Время подтверждённого возврата",
    )
    is_test = models.BooleanField(
        default=False,
        verbose_name="Тестовый платёж",
        help_text="True для тестового магазина ЮKassa / тестового контура",
    )
    form_url = models.URLField(
        max_length=2048,
        blank=True,
        default="",
        verbose_name="URL платёжной страницы",
    )
    sber_order_status = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="orderStatus из шлюза",
    )
    action_code = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="actionCode",
    )
    error_code = models.CharField(max_length=32, blank=True, default="")
    error_message = models.CharField(max_length=512, blank=True, default="")
    paid_at = models.DateTimeField(blank=True, null=True)
    callback_received_at = models.DateTimeField(blank=True, null=True)
    last_status_checked_at = models.DateTimeField(blank=True, null=True)
    register_response = models.JSONField(default=dict, blank=True)
    last_status_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_payment"
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            # Не больше одного успешного платежа на заказ
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status="paid"),
                name="payments_one_paid_per_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.merchant_order_number} [{self.status}]"

    @staticmethod
    def rubles_to_kopecks(amount: Decimal) -> int:
        quantized = Decimal(amount).quantize(Decimal("0.01"))
        return int(quantized * 100)
