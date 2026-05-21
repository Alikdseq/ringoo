"""
Сигналы бонусного приложения: создание BonusAccount при создании User;
начисление бонусов при подтверждении заказа (задача 2.1.6).
"""

from decimal import Decimal

from django.db.models.signals import post_save

from apps.bonus.models import BonusAccount
from apps.bonus.services import add_bonus, calculate_order_bonus
from apps.bonus.models import BonusTransaction


def create_bonus_account_for_new_user(sender, instance, created, **kwargs):
    """При создании пользователя автоматически создаём бонусный счёт."""
    if created:
        BonusAccount.objects.get_or_create(user=instance)


def award_bonus_on_order_confirmed(sender, instance, created, **kwargs):
    """
    При переходе заказа в статус 'confirmed' начислить бонусы на счёт пользователя.
    Начисление выполняется один раз (проверка по bonus_earned == 0).
    """
    from apps.orders.models import Order

    if instance.status != Order.STATUS_CONFIRMED:
        return
    if not instance.user_id:
        return
    if instance.bonus_earned and Decimal(instance.bonus_earned) > 0:
        return
    amount = calculate_order_bonus(instance)
    if amount <= 0:
        return
    account, _ = BonusAccount.objects.get_or_create(
        user_id=instance.user_id,
        defaults={},
    )
    add_bonus(
        account,
        amount,
        BonusTransaction.REASON_ORDER_REWARD,
        order=instance,
        description=f"Начисление за заказ {instance.order_number}",
    )
    Order.objects.filter(pk=instance.pk).update(bonus_earned=amount)
    instance.bonus_earned = amount  # keep in-memory in sync so repeated save() doesn't overwrite
