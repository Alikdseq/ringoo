"""FUNC-007: BONUS_ENABLED выключает скрытое начисление."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings

from apps.bonus.models import BonusAccount, BonusTransaction
from apps.orders.models import Order
from apps.products.models import Category, Product
from apps.stores.models import Store
from apps.users.models import CustomUser


def _order(user):
    cat = Category.objects.create(title="C", slug=f"b7-{Category.objects.count()}")
    product = Product.objects.create(
        title="P",
        slug=f"b7p-{Product.objects.count()}",
        price=Decimal("100.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"b7s-{Store.objects.count()}", address="a", city="c"
    )
    return Order.objects.create(
        user=user,
        full_name="U",
        phone=user.phone,
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=Order.PAYMENT_CASH,
        status=Order.STATUS_NEW,
        total_amount=Decimal("100.00"),
        consent_personal_data=True,
    )


class Func007BonusFlagTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone="79005550001", password="pass12345"
        )

    @override_settings(BONUS_ENABLED=False)
    def test_disabled_does_not_award(self):
        order = _order(self.user)
        order.status = Order.STATUS_CONFIRMED
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.bonus_earned, Decimal("0"))
        self.assertEqual(BonusTransaction.objects.count(), 0)

    @override_settings(BONUS_ENABLED=True)
    def test_enabled_awards(self):
        order = _order(self.user)
        order.status = Order.STATUS_CONFIRMED
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.bonus_earned, Decimal("5.00"))
        self.assertTrue(BonusAccount.objects.filter(user=self.user).exists())
