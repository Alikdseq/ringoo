"""
Unit-тесты для integrations.email_service (задача 2.4.2).
"""

from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings

from apps.orders.models import Order

from integrations.email_service import (
    send_manager_rating,
    send_order_confirmation,
    send_order_status_change,
)


@override_settings(DEFAULT_FROM_EMAIL="noreply@test.ringoo.local")
class TestSendOrderConfirmation(TestCase):
    def setUp(self):
        mail.outbox.clear()

    def test_sends_when_order_has_email(self):
        order = Order.objects.create(
            order_number="ORD-20260208-abc001",
            full_name="Иван Иванов",
            phone="+79991234567",
            email="customer@example.com",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("1500.00"),
            delivery_cost=Decimal("0"),
        )
        result = send_order_confirmation(order)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["customer@example.com"])
        self.assertIn("ORD-20260208-abc001", msg.subject)
        self.assertIn("1500", msg.body)
        self.assertEqual(msg.from_email, "noreply@test.ringoo.local")

    def test_sends_when_order_has_user_email(self):
        from apps.users.models import CustomUser

        user = CustomUser.objects.create_user(
            phone="+79990000000",
            username="+79990000000",
            email="user@example.com",
            password="pass",
        )
        order = Order.objects.create(
            order_number="ORD-20260208-abc002",
            user=user,
            full_name="Петр",
            phone="+79990000000",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("200.00"),
        )
        result = send_order_confirmation(order)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["user@example.com"])

    def test_returns_false_when_no_recipient(self):
        order = Order.objects.create(
            order_number="ORD-20260208-abc003",
            full_name="Без почты",
            phone="+79991111111",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100.00"),
        )
        result = send_order_confirmation(order)
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(DEFAULT_FROM_EMAIL="noreply@test.ringoo.local")
class TestSendOrderStatusChange(TestCase):
    def setUp(self):
        mail.outbox.clear()

    def test_sends_with_old_and_new_status(self):
        order = Order.objects.create(
            order_number="ORD-20260208-xyz001",
            full_name="Мария",
            phone="+79992222222",
            email="maria@example.com",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("500.00"),
            status=Order.STATUS_CONFIRMED,
        )
        result = send_order_status_change(order, old_status=Order.STATUS_NEW)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["maria@example.com"])
        self.assertIn("ORD-20260208-xyz001", msg.subject)
        self.assertIn("Новый", msg.body)
        self.assertIn("Подтверждён", msg.body)

    def test_returns_false_when_no_recipient(self):
        order = Order.objects.create(
            order_number="ORD-20260208-xyz002",
            full_name="Без почты",
            phone="+79993333333",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100.00"),
            status=Order.STATUS_IN_PROGRESS,
        )
        result = send_order_status_change(order, old_status=Order.STATUS_CONFIRMED)
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(DEFAULT_FROM_EMAIL="noreply@test.ringoo.local")
class TestSendManagerRating(TestCase):
    def setUp(self):
        mail.outbox.clear()

    def test_sends_with_rating_and_comment(self):
        result = send_manager_rating(
            to_email="manager@example.com",
            order_number="ORD-20260208-001",
            rating=5,
            comment="Всё отлично!",
        )
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["manager@example.com"])
        self.assertIn("ORD-20260208-001", msg.subject)
        self.assertIn("5", msg.body)
        self.assertIn("Всё отлично!", msg.body)

    def test_sends_without_comment(self):
        result = send_manager_rating(
            to_email="admin@example.com",
            order_number="ORD-20260208-002",
            rating=4,
        )
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("4", mail.outbox[0].body)

    def test_returns_false_when_to_email_empty(self):
        result = send_manager_rating(
            to_email="",
            order_number="ORD-20260208-003",
            rating=3,
        )
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
