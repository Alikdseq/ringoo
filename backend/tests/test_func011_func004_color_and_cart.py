"""FUNC-011 цвет в заказе + FUNC-004 очистка корзины по цвету."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.cart.checkout_clear import clear_cart_after_successful_payment
from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product, ProductColor
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
    BONUS_ENABLED=False,
    SBER_ECOM_ENABLED=False,
    YOOKASSA_ENABLED=False,
)
class Func011ColorAndCartClearTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = CustomUser.objects.create_user(
            phone="79003330001", password="pass12345"
        )
        self.cat = Category.objects.create(title="C", slug="f11c")
        self.product = Product.objects.create(
            title="Phone",
            slug="f11p",
            price=Decimal("1000.00"),
            category=self.cat,
            is_active=True,
        )
        self.color_black = ProductColor.objects.create(
            product=self.product,
            slug="black",
            label="Чёрный",
            hex="#000000",
            price=Decimal("1000.00"),
            is_active=True,
        )
        self.color_white = ProductColor.objects.create(
            product=self.product,
            slug="white",
            label="Белый",
            hex="#ffffff",
            price=Decimal("1100.00"),
            is_active=True,
        )
        self.store = Store.objects.create(
            name="S", slug="f11s", address="a", city="Москва", is_active=True
        )
        Stock.objects.create(
            product=self.product, store=self.store, quantity=20, reserved_quantity=0
        )

    def test_order_keeps_color_snapshot_and_server_price(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/api/v1/orders/",
            {
                "full_name": "Buyer",
                "phone": self.user.phone,
                "delivery_type": "pickup",
                "store": str(self.store.id),
                "payment_type": "cash",
                "items": [
                    {
                        "product_id": str(self.product.id),
                        "quantity": 1,
                        "color_id": str(self.color_white.id),
                        "price": "1.00",
                    }
                ],
                "total_amount": "1.00",
                "delivery_cost": "0",
                "bonus_used": "0",
                "consent_personal_data": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body["total_amount"], "1100.00")
        item = body["items"][0]
        self.assertEqual(item["color_label"], "Белый")
        self.assertEqual(item["color_slug"], "white")
        self.assertEqual(item["price"], "1100.00")
        oi = OrderItem.objects.get(order_id=body["id"])
        self.assertEqual(oi.color_id, self.color_white.id)

    def test_wrong_product_color_rejected(self):
        other = Product.objects.create(
            title="Other",
            slug="f11o",
            price=Decimal("500.00"),
            category=self.cat,
            is_active=True,
        )
        Stock.objects.create(
            product=other, store=self.store, quantity=5, reserved_quantity=0
        )
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/api/v1/orders/",
            {
                "full_name": "Buyer",
                "phone": self.user.phone,
                "delivery_type": "pickup",
                "store": str(self.store.id),
                "payment_type": "cash",
                "items": [
                    {
                        "product_id": str(other.id),
                        "quantity": 1,
                        "color_id": str(self.color_black.id),
                    }
                ],
                "total_amount": "500.00",
                "consent_personal_data": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_color_required_when_product_has_colors(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/api/v1/orders/",
            {
                "full_name": "Buyer",
                "phone": self.user.phone,
                "delivery_type": "pickup",
                "store": str(self.store.id),
                "payment_type": "cash",
                "items": [{"product_id": str(self.product.id), "quantity": 1}],
                "total_amount": "1000.00",
                "consent_personal_data": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_cart_clear_respects_color(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            store=self.store,
            color=self.color_black,
            quantity=2,
            price_at_add=Decimal("1000.00"),
        )
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            store=self.store,
            color=self.color_white,
            quantity=2,
            price_at_add=Decimal("1100.00"),
        )
        order = Order.objects.create(
            user=self.user,
            full_name="B",
            phone=self.user.phone,
            delivery_type=Order.DELIVERY_PICKUP,
            store=self.store,
            payment_type=Order.PAYMENT_ONLINE,
            status=Order.STATUS_CONFIRMED,
            total_amount=Decimal("1000.00"),
            consent_personal_data=True,
            checkout_cart_id=cart.pk,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_title=self.product.title,
            quantity=1,
            price=Decimal("1000.00"),
            item_total=Decimal("1000.00"),
            color=self.color_black,
            color_label="Чёрный",
            color_slug="black",
        )
        report = clear_cart_after_successful_payment(order)
        self.assertEqual(report["qty_removed"], 1)
        black = CartItem.objects.get(cart=cart, color=self.color_black)
        white = CartItem.objects.get(cart=cart, color=self.color_white)
        self.assertEqual(black.quantity, 1)
        self.assertEqual(white.quantity, 2)
