"""
Бонусная система: BonusAccount, BonusTransaction (задачи 2.1.1, 2.1.2).
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class BonusAccount(models.Model):
    """
    Бонусный счёт пользователя. Создаётся автоматически при создании User (сигнал).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bonus_account",
        verbose_name="Пользователь",
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Баланс",
    )
    total_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Всего начислено",
    )
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Всего списано",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    class Meta:
        db_table = "bonus_bonusaccount"
        verbose_name = "Бонусный счёт"
        verbose_name_plural = "Бонусные счета"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"Бонусы: {self.user_id} ({self.balance})"


class BonusTransaction(models.Model):
    """
    Транзакция по бонусному счёту (начисление или списание).
    """

    REASON_ORDER_REWARD = "order_reward"
    REASON_ORDER_REFUND = "order_refund"
    REASON_ADMIN_ADJUST = "admin_adjust"
    REASON_ORDER_SPEND = "order_spend"
    REASON_CHOICES = [
        (REASON_ORDER_REWARD, "Начисление за заказ"),
        (REASON_ORDER_REFUND, "Возврат по заказу"),
        (REASON_ADMIN_ADJUST, "Корректировка администратором"),
        (REASON_ORDER_SPEND, "Списание при заказе"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    account = models.ForeignKey(
        BonusAccount,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Бонусный счёт",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма",
        help_text="Положительная — начисление, отрицательная — списание",
    )
    reason = models.CharField(
        max_length=32,
        choices=REASON_CHOICES,
        verbose_name="Причина",
    )
    related_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bonus_transactions",
        verbose_name="Связанный заказ",
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Описание",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )

    class Meta:
        db_table = "bonus_bonustransaction"
        verbose_name = "Бонусная транзакция"
        verbose_name_plural = "Бонусные транзакции"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["reason"]),
            models.Index(fields=["related_order"]),
        ]

    def __str__(self):
        return f"{self.get_reason_display()}: {self.amount} ({self.created_at})"
