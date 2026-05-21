"""
Unit-тесты приложения orders (задачи 1.5.3, 1.5.4, 1.5.5).
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Store, Stock
from apps.users.models import CustomUser

from .models import Order, OrderItem
from .tasks import send_order_notifications
from .delivery_address import normalize_delivery_address
from .serializers import (
    OrderCreateSerializer,
    OrderItemSerializer,
    OrderSerializer,
)


class TestOrderItemSerializer(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            order_number="ORD-20260207-abc123",
            full_name="Иван Иванов",
            phone="+79991234567",
            delivery_type=Order.DELIVERY_DELIVERY,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("500.00"),
            delivery_address={"city": "Москва", "street": "Ленина", "house": "1"},
        )
        self.item = OrderItem.objects.create(
            order=self.order,
            product_title="Товар",
            quantity=2,
            price=Decimal("250.00"),
            item_total=Decimal("500.00"),
        )

    def test_order_item_serializer_fields(self):
        data = OrderItemSerializer(self.item).data
        self.assertEqual(data["id"], str(self.item.id))
        self.assertEqual(data["product_title"], "Товар")
        self.assertEqual(data["quantity"], 2)
        self.assertEqual(data["price"], "250.00")
        self.assertEqual(data["item_total"], "500.00")


class TestOrderSerializer(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            order_number="ORD-20260207-xyz",
            full_name="Петр",
            phone="+79990000000",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CARD_ON_DELIVERY,
            total_amount=Decimal("100.00"),
        )
        OrderItem.objects.create(
            order=self.order,
            product_title="Товар 1",
            quantity=1,
            price=Decimal("100.00"),
            item_total=Decimal("100.00"),
        )

    def test_order_serializer_includes_items(self):
        data = OrderSerializer(self.order).data
        self.assertIn("items", data)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["product_title"], "Товар 1")
        self.assertEqual(data["order_number"], "ORD-20260207-xyz")


class TestOrderCreateSerializer(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=self.category,
        )
        self.store = Store.objects.create(
            name="М",
            slug="m",
            address="А",
            city="Москва",
        )

    def test_items_cannot_be_empty(self):
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "delivery",
            "delivery_address": {"city": "М", "street": "С", "house": "1"},
            "payment_type": "cash",
            "items": [],
            "total_amount": Decimal("0"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("items", s.errors)

    def test_delivery_requires_address(self):
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "delivery",
            "delivery_address": {},
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": Decimal("100.00"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("delivery_address", s.errors)

    def test_client_price_ignored_total_from_catalog(self):
        """Цена и total_amount с клиента не определяют сумму — только каталог и доставка."""
        self.product.price = Decimal("250.00")
        self.product.save(update_fields=["price"])
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "pickup",
            "payment_type": "cash",
            "store": str(self.store.id),
            "items": [
                {"product_id": str(self.product.id), "quantity": 2, "price": "1.00"}
            ],
            "total_amount": Decimal("2.00"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["items"][0]["price"], Decimal("250.00"))
        self.assertEqual(s.validated_data["total_amount"], Decimal("500.00"))

    def test_valid_data_passes(self):
        data = {
            "full_name": "Test User",
            "phone": "+79991234567",
            "delivery_type": "pickup",
            "payment_type": "cash",
            "store": str(self.store.id),
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": Decimal("100.00"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_bonus_used_negative_invalid(self):
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "pickup",
            "payment_type": "cash",
            "store": str(self.store.id),
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": Decimal("100.00"),
            "bonus_used": Decimal("-10"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("bonus_used", s.errors)

    def test_delivery_address_unknown_key_rejected(self):
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "delivery",
            "delivery_address": {
                "city": "М",
                "street": "С",
                "house": "1",
                "extra_field": "x",
            },
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": Decimal("100.00"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("delivery_address", s.errors)

    def test_pickup_requires_store(self):
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "pickup",
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": Decimal("100.00"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("store", s.errors)

    def test_pickup_inactive_store_rejected(self):
        self.store.is_active = False
        self.store.save(update_fields=["is_active"])
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "pickup",
            "payment_type": "cash",
            "store": str(self.store.id),
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": Decimal("100.00"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("store", s.errors)

    def test_delivery_rejects_store(self):
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "delivery",
            "delivery_address": {"city": "М", "street": "С", "house": "1"},
            "payment_type": "cash",
            "store": str(self.store.id),
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": Decimal("100.00"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("store", s.errors)

    def test_pickup_unknown_store_uuid_rejected(self):
        data = {
            "full_name": "Test",
            "phone": "+7",
            "delivery_type": "pickup",
            "payment_type": "cash",
            "store": str(uuid.uuid4()),
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": Decimal("100.00"),
            "consent_personal_data": True,
        }
        s = OrderCreateSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("store", s.errors)


class TestNormalizeDeliveryAddress(TestCase):
    def test_strips_and_keeps_allowed_keys(self):
        d = normalize_delivery_address(
            {"city": " Москва ", "street": "Ленина", "house": "10", "apartment": ""}
        )
        self.assertEqual(d["city"], "Москва")
        self.assertNotIn("apartment", d)

    def test_nested_value_rejected(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            normalize_delivery_address({"city": {"x": 1}})


# --- API (1.5.4, 1.5.5) ---


class TestOrderListCreateViewAPI(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="М",
            slug="m",
            address="А",
            city="Москва",
            is_active=True,
        )
        Stock.objects.create(product=self.product, store=self.store, quantity=10)

    def test_get_list_requires_auth(self):
        url = reverse("api_v1:orders:order-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_get_list_returns_user_orders(self):
        user = CustomUser.objects.create_user(
            phone="+79991111111", email="listuser@test.com"
        )
        Order.objects.create(
            order_number="ORD-TEST-001",
            user=user,
            full_name="U",
            phone="+7",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("50"),
        )
        self.client.force_authenticate(user=user)
        url = reverse("api_v1:orders:order-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["order_number"], "ORD-TEST-001")

    def test_get_list_idor_excludes_other_users_orders(self):
        """§10.2.2: список заказов только своих (чужой заказ не попадает в выдачу)."""
        owner = CustomUser.objects.create_user(
            phone="+79991111112", email="owner2@test.com"
        )
        other = CustomUser.objects.create_user(
            phone="+79991111113", email="other2@test.com"
        )
        Order.objects.create(
            order_number="ORD-MINE-001",
            user=owner,
            full_name="Owner",
            phone="+7",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("10"),
        )
        Order.objects.create(
            order_number="ORD-THEIRS-001",
            user=other,
            full_name="Other",
            phone="+7",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("20"),
        )
        self.client.force_authenticate(user=owner)
        url = reverse("api_v1:orders:order-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        numbers = {r["order_number"] for r in response.json().get("results", [])}
        self.assertEqual(numbers, {"ORD-MINE-001"})
        self.assertNotIn("ORD-THEIRS-001", numbers)

    def test_post_create_order_with_items(self):
        url = reverse("api_v1:orders:order-list-create")
        payload = {
            "full_name": "Иван",
            "phone": "+79991234567",
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 2, "price": "100.00"}
            ],
            "total_amount": "200.00",
            "consent_personal_data": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("order_number", data)
        self.assertEqual(data["total_amount"], "200.00")
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 2)

    def test_post_pickup_reserves_network_stock_not_only_selected_store(self):
        """Самовывоз: резерв по сети; остаток может быть не в выбранной точке."""
        other = Store.objects.create(
            name="Другой",
            slug="other",
            address="Б",
            city="Москва",
            is_active=True,
        )
        Stock.objects.filter(product=self.product, store=self.store).update(quantity=0)
        Stock.objects.create(product=self.product, store=other, quantity=10)
        url = reverse("api_v1:orders:order-list-create")
        payload = {
            "full_name": "Иван",
            "phone": "+79991234567",
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 2, "price": "100.00"}
            ],
            "total_amount": "200.00",
            "consent_personal_data": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()["store"], str(self.store.id))

    def test_post_from_cart_empty_returns_400(self):
        url = reverse("api_v1:orders:order-list-create")
        response = self.client.post(
            url,
            {"from_cart": True, "full_name": "X", "phone": "+7", "delivery_type": "delivery", "delivery_address": {"city": "M", "street": "S", "house": "1"}, "payment_type": "cash"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("code"), "ORDER_INVALID_ITEMS")

    def test_post_pickup_without_store_returns_400(self):
        url = reverse("api_v1:orders:order-list-create")
        payload = {
            "full_name": "Иван",
            "phone": "+79991234567",
            "delivery_type": "pickup",
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": "100.00",
            "consent_personal_data": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("store", response.json())

    def test_post_pickup_insufficient_stock_returns_400(self):
        Stock.objects.filter(product=self.product, store=self.store).update(quantity=1)
        url = reverse("api_v1:orders:order-list-create")
        payload = {
            "full_name": "Иван",
            "phone": "+79991234567",
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 5, "price": "100.00"}
            ],
            "total_amount": "500.00",
            "consent_personal_data": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("code"), "INSUFFICIENT_STOCK")

    def test_post_delivery_reserves_stock_across_stores(self):
        s2 = Store.objects.create(
            name="М2",
            slug="m2",
            address="Б",
            city="Москва",
            is_active=True,
        )
        Stock.objects.filter(product=self.product, store=self.store).update(quantity=2)
        Stock.objects.create(product=self.product, store=s2, quantity=2)
        url = reverse("api_v1:orders:order-list-create")
        payload = {
            "full_name": "Иван",
            "phone": "+79991234567",
            "delivery_type": "delivery",
            "delivery_address": {"city": "Москва", "street": "Ленина", "house": "1"},
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 4, "price": "1.00"}
            ],
            "total_amount": "4.00",
            "consent_personal_data": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()["total_amount"], "400.00")
        row1 = Stock.objects.get(product=self.product, store=self.store)
        row2 = Stock.objects.get(product=self.product, store=s2)
        self.assertEqual(row1.reserved_quantity + row2.reserved_quantity, 4)
        self.assertEqual(row1.reserved_quantity, 2)
        self.assertEqual(row2.reserved_quantity, 2)

    def test_post_delivery_insufficient_aggregate_stock_returns_400(self):
        Stock.objects.filter(product=self.product, store=self.store).update(quantity=1)
        url = reverse("api_v1:orders:order-list-create")
        payload = {
            "full_name": "Иван",
            "phone": "+79991234567",
            "delivery_type": "delivery",
            "delivery_address": {"city": "Москва", "street": "Ленина", "house": "1"},
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 5, "price": "100.00"}
            ],
            "total_amount": "500.00",
            "consent_personal_data": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("code"), "INSUFFICIENT_STOCK")


class TestOrderDetailViewAPI(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            phone="+79992222222", email="owner@test.com"
        )
        self.other = CustomUser.objects.create_user(
            phone="+79993333333", email="other@test.com"
        )
        self.order = Order.objects.create(
            order_number="ORD-OWN-001",
            user=self.user,
            full_name="Owner",
            phone="+7",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100"),
        )

    def test_get_detail_as_owner_200(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api_v1:orders:order-detail", kwargs={"pk": self.order.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["order_number"], "ORD-OWN-001")

    def test_get_detail_as_other_404(self):
        self.client.force_authenticate(user=self.other)
        url = reverse("api_v1:orders:order-detail", kwargs={"pk": self.order.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestSendOrderNotificationsIdempotent(TestCase):
    """§9.2.3: повторная доставка Celery не шлёт письмо подтверждения снова."""

    @patch("integrations.email_service.send_order_confirmation", return_value=True)
    def test_second_task_run_skips_send(self, mock_send):
        order = Order.objects.create(
            order_number="ORD-IDEM-001",
            full_name="Тест",
            phone="+79991111111",
            email="t@example.com",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100"),
        )
        r1 = send_order_notifications(order.id)
        self.assertTrue(r1.get("sent"))
        r2 = send_order_notifications(order.id)
        self.assertTrue(r2.get("skipped"))
        self.assertEqual(r2.get("reason"), "already_sent")
        mock_send.assert_called_once()
        order.refresh_from_db()
        self.assertIsNotNone(order.confirmation_email_sent_at)
