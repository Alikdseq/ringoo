"""INT-026: reorder сохраняет color и store."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cart.models import CartItem
from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product, ProductColor
from apps.stores.models import Stock, Store


User = get_user_model()


class ReorderColorStoreTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="79001234567",
            email="reorder@example.com",
            password="pass12345",
        )
        cat = Category.objects.create(title="C", slug="reord-c")
        self.product = Product.objects.create(
            title="Phone",
            slug="reord-p",
            price=Decimal("1000"),
            category=cat,
            is_active=True,
        )
        self.color = ProductColor.objects.create(
            product=self.product,
            label="Red",
            slug="red",
            hex="#ff0000",
            is_active=True,
            price=Decimal("1100"),
        )
        self.store = Store.objects.create(
            name="Shop", slug="reord-s", address="a", city="c", is_active=True
        )
        Stock.objects.create(
            product=self.product, store=self.store, quantity=10, reserved_quantity=0
        )
        self.order = Order.objects.create(
            user=self.user,
            full_name="U",
            phone="79001234567",
            delivery_type=Order.DELIVERY_PICKUP,
            store=self.store,
            payment_type=Order.PAYMENT_CASH,
            status=Order.STATUS_COMPLETED,
            total_amount=Decimal("1100"),
            consent_personal_data=True,
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_title=self.product.title,
            quantity=1,
            price=Decimal("1100"),
            item_total=Decimal("1100"),
            color=self.color,
            color_label="Red",
            color_slug="red",
            color_hex="#ff0000",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_reorder_keeps_color_and_store(self):
        res = self.api.post(f"/api/v1/orders/{self.order.pk}/reorder/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["added_count"], 1)
        self.assertFalse(body["partial"])
        item = CartItem.objects.get(cart_id=body["cart"]["id"])
        self.assertEqual(item.color_id, self.color.pk)
        self.assertEqual(item.store_id, self.store.pk)
        self.assertEqual(item.price_at_add, Decimal("1100"))

    def test_reorder_skips_inactive_color(self):
        self.color.is_active = False
        self.color.save(update_fields=["is_active"])
        res = self.api.post(f"/api/v1/orders/{self.order.pk}/reorder/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["added_count"], 0)
        self.assertTrue(body["partial"])
        self.assertEqual(body["skipped"][0]["reason"], "color_unavailable")
