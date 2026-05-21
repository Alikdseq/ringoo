"""
Unit-тесты бонусов: сервисы (2.1.3), сериализаторы (2.1.4), API (2.1.5).
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.users.models import CustomUser

from .models import BonusAccount, BonusTransaction
from .services import add_bonus, calculate_order_bonus, spend_bonus


class TestAddBonus(TestCase):
    """Тесты add_bonus."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone="+79991234567",
            username="+79991234567",
            password="testpass123",
        )
        self.account = BonusAccount.objects.get(user=self.user)

    def test_add_bonus_increases_balance_and_total_earned(self):
        txn = add_bonus(
            self.account,
            Decimal("100.00"),
            BonusTransaction.REASON_ORDER_REWARD,
            description="Тест",
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("100.00"))
        self.assertEqual(self.account.total_earned, Decimal("100.00"))
        self.assertEqual(txn.amount, Decimal("100.00"))
        self.assertEqual(txn.reason, BonusTransaction.REASON_ORDER_REWARD)
        self.assertEqual(txn.description, "Тест")

    def test_add_bonus_twice_cumulative(self):
        add_bonus(
            self.account,
            Decimal("50.00"),
            BonusTransaction.REASON_ADMIN_ADJUST,
        )
        add_bonus(
            self.account,
            Decimal("30.00"),
            BonusTransaction.REASON_ORDER_REWARD,
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("80.00"))
        self.assertEqual(self.account.total_earned, Decimal("80.00"))

    def test_add_bonus_negative_raises(self):
        with self.assertRaises(ValueError) as ctx:
            add_bonus(
                self.account,
                Decimal("-10.00"),
                BonusTransaction.REASON_ORDER_REWARD,
            )
        self.assertIn("positive", str(ctx.exception).lower())


class TestSpendBonus(TestCase):
    """Тесты spend_bonus."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone="+79997654321",
            username="+79997654321",
            password="testpass123",
        )
        self.account = BonusAccount.objects.get(user=self.user)
        self.order = Order.objects.create(
            order_number="ORD-TEST-001",
            full_name="Test",
            phone="+79991234567",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100.00"),
        )

    def test_spend_bonus_decreases_balance_increases_total_spent(self):
        add_bonus(
            self.account,
            Decimal("50.00"),
            BonusTransaction.REASON_ADMIN_ADJUST,
        )
        txn = spend_bonus(self.account, Decimal("20.00"), self.order)
        self.assertIsNotNone(txn)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("30.00"))
        self.assertEqual(self.account.total_spent, Decimal("20.00"))
        self.assertEqual(txn.amount, Decimal("-20.00"))
        self.assertEqual(txn.reason, BonusTransaction.REASON_ORDER_SPEND)
        self.assertEqual(txn.related_order_id, self.order.id)

    def test_spend_bonus_insufficient_balance_returns_none(self):
        add_bonus(
            self.account,
            Decimal("10.00"),
            BonusTransaction.REASON_ORDER_REWARD,
        )
        txn = spend_bonus(self.account, Decimal("50.00"), self.order)
        self.assertIsNone(txn)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("10.00"))
        self.assertEqual(self.account.total_spent, Decimal("0"))

    def test_spend_bonus_zero_balance_returns_none(self):
        txn = spend_bonus(self.account, Decimal("1.00"), self.order)
        self.assertIsNone(txn)

    def test_spend_bonus_negative_amount_raises(self):
        add_bonus(self.account, Decimal("10.00"), BonusTransaction.REASON_ADMIN_ADJUST)
        with self.assertRaises(ValueError) as ctx:
            spend_bonus(self.account, Decimal("-5.00"), self.order)
        self.assertIn("positive", str(ctx.exception).lower())


class TestCalculateOrderBonus(TestCase):
    """Тесты calculate_order_bonus."""

    def test_calculate_5_percent_of_total(self):
        order = Order(
            order_number="ORD-X",
            full_name="X",
            phone="+7",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100.00"),
        )
        self.assertEqual(calculate_order_bonus(order), Decimal("5.00"))

    def test_calculate_rounds_to_two_decimals(self):
        order = Order(
            order_number="ORD-X",
            full_name="X",
            phone="+7",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("99.99"),
        )
        self.assertEqual(calculate_order_bonus(order), Decimal("5.00"))

    def test_calculate_zero_total_returns_zero(self):
        order = Order(
            order_number="ORD-X",
            full_name="X",
            phone="+7",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("0"),
        )
        self.assertEqual(calculate_order_bonus(order), Decimal("0"))

    def test_calculate_no_total_amount_returns_zero(self):
        class FakeOrder:
            pass

        self.assertEqual(calculate_order_bonus(FakeOrder()), Decimal("0"))


class TestBonusSerializers(TestCase):
    """Тесты сериализаторов бонусов (задача 2.1.4)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone="+79991111111",
            username="+79991111111",
            password="testpass123",
        )
        self.account = BonusAccount.objects.get(user=self.user)
        self.order = Order.objects.create(
            order_number="ORD-SER-001",
            full_name="Test",
            phone="+79991234567",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100.00"),
        )

    def test_bonus_transaction_serializer_fields(self):
        from .serializers import BonusTransactionSerializer

        add_bonus(
            self.account,
            Decimal("25.00"),
            BonusTransaction.REASON_ORDER_REWARD,
            order=self.order,
            description="За заказ",
        )
        txn = self.account.transactions.first()
        data = BonusTransactionSerializer(txn).data
        self.assertEqual(str(txn.id), data["id"])
        self.assertEqual("25.00", data["amount"])
        self.assertEqual(BonusTransaction.REASON_ORDER_REWARD, data["reason"])
        self.assertIn("reason_display", data)
        self.assertEqual(str(data["related_order"]), str(self.order.id))
        self.assertEqual("За заказ", data["description"])
        self.assertIn("created_at", data)

    def test_bonus_account_serializer_fields_and_nested_transactions(self):
        from .serializers import BonusAccountSerializer

        add_bonus(
            self.account,
            Decimal("10.00"),
            BonusTransaction.REASON_ADMIN_ADJUST,
        )
        txns_page = list(self.account.transactions.all()[:10])
        context = {"transactions": txns_page}
        data = BonusAccountSerializer(
            self.account, context=context
        ).data
        self.assertEqual(str(self.account.id), data["id"])
        self.assertEqual("10.00", data["balance"])
        self.assertEqual("10.00", data["total_earned"])
        self.assertEqual("0.00", data["total_spent"])
        self.assertIn("updated_at", data)
        self.assertIsInstance(data["transactions"], list)
        self.assertEqual(len(data["transactions"]), 1)
        self.assertEqual(data["transactions"][0]["amount"], "10.00")

    def test_bonus_account_serializer_empty_transactions_without_context(self):
        from .serializers import BonusAccountSerializer

        data = BonusAccountSerializer(self.account).data
        self.assertEqual(data["transactions"], [])


@override_settings(
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False}
)
class TestBonusAPI(TestCase):
    """Тесты API бонусов (задача 2.1.5)."""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            phone="+79995555555",
            username="+79995555555",
            password="testpass123",
        )
        self.account = BonusAccount.objects.get(user=self.user)

    def test_bonus_account_get_requires_auth(self):
        url = reverse("api_v1:bonus:account")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bonus_account_get_returns_balance_and_transactions(self):
        add_bonus(
            self.account,
            Decimal("50.00"),
            BonusTransaction.REASON_ADMIN_ADJUST,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("api_v1:bonus:account")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("balance", data)
        self.assertEqual(data["balance"], "50.00")
        self.assertIn("transactions", data)
        self.assertEqual(len(data["transactions"]), 1)
        self.assertEqual(data["transactions"][0]["amount"], "50.00")

    def test_bonus_transactions_list_requires_auth(self):
        url = reverse("api_v1:bonus:transactions")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bonus_transactions_list_paginated(self):
        add_bonus(
            self.account,
            Decimal("10.00"),
            BonusTransaction.REASON_ORDER_REWARD,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("api_v1:bonus:transactions")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["amount"], "10.00")

    def test_bonus_transactions_filter_by_reason(self):
        add_bonus(
            self.account,
            Decimal("5.00"),
            BonusTransaction.REASON_ORDER_REWARD,
        )
        add_bonus(
            self.account,
            Decimal("3.00"),
            BonusTransaction.REASON_ADMIN_ADJUST,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("api_v1:bonus:transactions")
        response = self.client.get(
            url, {"reason": BonusTransaction.REASON_ORDER_REWARD}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["reason"], BonusTransaction.REASON_ORDER_REWARD)


class TestBonusOnOrderConfirmed(TestCase):
    """Тесты начисления бонусов при подтверждении заказа (задача 2.1.6)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone="+79998887777",
            username="+79998887777",
            password="testpass123",
        )
        self.account = BonusAccount.objects.get(user=self.user)

    def test_order_confirmed_awards_bonus_and_updates_bonus_earned(self):
        order = Order.objects.create(
            order_number="ORD-CONF-001",
            user=self.user,
            full_name="Test",
            phone="+79991234567",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100.00"),
            status=Order.STATUS_NEW,
        )
        self.assertEqual(order.bonus_earned, Decimal("0"))
        order.status = Order.STATUS_CONFIRMED
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.bonus_earned, Decimal("5.00"))  # 5% of 100
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("5.00"))
        txn = self.account.transactions.filter(
            reason=BonusTransaction.REASON_ORDER_REWARD
        ).first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.amount, Decimal("5.00"))
        self.assertEqual(txn.related_order_id, order.id)

    def test_order_confirmed_without_user_does_not_award(self):
        order = Order.objects.create(
            order_number="ORD-GUEST-001",
            user=None,
            full_name="Guest",
            phone="+79991111111",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("200.00"),
            status=Order.STATUS_CONFIRMED,
        )
        order.refresh_from_db()
        self.assertEqual(order.bonus_earned, Decimal("0"))
        self.assertEqual(
            BonusTransaction.objects.filter(related_order=order).count(), 0
        )

    def test_order_confirmed_twice_awards_only_once(self):
        order = Order.objects.create(
            order_number="ORD-TWICE-001",
            user=self.user,
            full_name="Test",
            phone="+79991234567",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100.00"),
            status=Order.STATUS_CONFIRMED,
        )
        order.refresh_from_db()
        self.assertEqual(order.bonus_earned, Decimal("5.00"))
        self.account.refresh_from_db()
        balance_after_first = self.account.balance
        order.save()  # save again without changing status
        order.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, balance_after_first)
        self.assertEqual(
            self.account.transactions.filter(
                reason=BonusTransaction.REASON_ORDER_REWARD
            ).count(),
            1,
        )
