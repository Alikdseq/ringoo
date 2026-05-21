"""
Сервисный слой бонусной системы (задача 2.1.3).
Начисление, списание и расчёт бонусов за заказ. Атомарные обновления через F().
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import F

from .models import BonusAccount, BonusTransaction


# Процент начисления бонусов от суммы заказа (правило по ТЗ: например 5%)
ORDER_BONUS_PERCENT = Decimal("5.00")


def add_bonus(account, amount, reason, order=None, description=None):
    """
    Начислить бонусы на счёт.

    - Создаёт BonusTransaction с положительным amount.
    - Атомарно обновляет balance и total_earned через F().
    - Возвращает созданную транзакцию.

    :param account: BonusAccount
    :param amount: Decimal, положительная сумма
    :param reason: одна из BonusTransaction.REASON_*
    :param order: Order или None
    :param description: str или None
    :return: BonusTransaction
    """
    amount = Decimal(amount)
    if amount <= 0:
        raise ValueError("add_bonus: amount must be positive")
    with transaction.atomic():
        BonusAccount.objects.filter(pk=account.pk).select_for_update().update(
            balance=F("balance") + amount,
            total_earned=F("total_earned") + amount,
        )
        account.refresh_from_db()
        txn = BonusTransaction.objects.create(
            account=account,
            amount=amount,
            reason=reason,
            related_order=order,
            description=description or "",
        )
    return txn


def spend_bonus(account, amount, order):
    """
    Списать бонусы со счёта.

    - Проверяет balance >= amount.
    - Создаёт BonusTransaction с отрицательным amount.
    - Атомарно обновляет balance и total_spent через F().
    - Возвращает транзакцию или None при недостатке средств.

    :param account: BonusAccount
    :param amount: Decimal, положительная сумма к списанию
    :param order: Order (связанный заказ)
    :return: BonusTransaction или None
    """
    amount = Decimal(amount)
    if amount <= 0:
        raise ValueError("spend_bonus: amount must be positive")
    with transaction.atomic():
        acc = BonusAccount.objects.select_for_update().get(pk=account.pk)
        if acc.balance < amount:
            return None
        BonusAccount.objects.filter(pk=acc.pk).update(
            balance=F("balance") - amount,
            total_spent=F("total_spent") + amount,
        )
        acc.refresh_from_db()
        txn = BonusTransaction.objects.create(
            account=acc,
            amount=-amount,
            reason=BonusTransaction.REASON_ORDER_SPEND,
            related_order=order,
            description=None,
        )
    return txn


def admin_adjust(account, amount, description=None):
    """
    Ручная корректировка бонусов администратором.
    amount > 0 — начисление, amount < 0 — списание (проверка баланса).
    :param account: BonusAccount
    :param amount: Decimal (положительная или отрицательная сумма)
    :param description: str или None
    :return: BonusTransaction
    """
    amount = Decimal(amount)
    if amount == 0:
        raise ValueError("admin_adjust: amount cannot be zero")
    description = description or ""
    with transaction.atomic():
        acc = BonusAccount.objects.select_for_update().get(pk=account.pk)
        if amount > 0:
            BonusAccount.objects.filter(pk=acc.pk).update(
                balance=F("balance") + amount,
                total_earned=F("total_earned") + amount,
            )
            txn = BonusTransaction.objects.create(
                account=acc,
                amount=amount,
                reason=BonusTransaction.REASON_ADMIN_ADJUST,
                related_order=None,
                description=description,
            )
        else:
            abs_amount = -amount
            if acc.balance < abs_amount:
                raise ValueError("Недостаточно бонусов на счёте для списания.")
            BonusAccount.objects.filter(pk=acc.pk).update(
                balance=F("balance") - abs_amount,
                total_spent=F("total_spent") + abs_amount,
            )
            txn = BonusTransaction.objects.create(
                account=acc,
                amount=-abs_amount,
                reason=BonusTransaction.REASON_ADMIN_ADJUST,
                related_order=None,
                description=description,
            )
        return txn


def calculate_order_bonus(order):
    """
    Рассчитать сумму бонусов к начислению за заказ (правило: процент от суммы).

    :param order: Order (должен иметь total_amount)
    :return: Decimal, сумма бонусов (>= 0)
    """
    total = getattr(order, "total_amount", None)
    if total is None:
        return Decimal("0")
    total = Decimal(total)
    if total <= 0:
        return Decimal("0")
    return (total * ORDER_BONUS_PERCENT / Decimal("100")).quantize(Decimal("0.01"))
