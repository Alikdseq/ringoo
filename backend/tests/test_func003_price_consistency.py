"""FUNC-003: согласованность цен корзины и заказа."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
    BONUS_ENABLED=False,
)
class Func003PriceConsistencyTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = CustomUser.objects.create_user(
            phone="79004440001", password="pass12345"
        )
        cat = Category.objects.create(title="C", slug="f3c")
        self.product = Product.objects.create(
            title="P",
            slug="f3p",
            price=Decimal("200.00"),
            category=cat,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="S", slug="f3s", address="a", city="c", is_active=True
        )
        Stock.objects.create(
            product=self.product, store=self.store, quantity=10, reserved_quantity=0
        )
        self.api.force_authenticate(user=self.user)

    def _payload(self, *, expected="200.00", accept=False, client_price="1.00"):
        return {
            "full_name": "Buyer",
            "phone": self.user.phone,
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": "cash",
            "items": [
                {
                    "product_id": str(self.product.id),
                    "quantity": 1,
                    "price": client_price,
                    "expected_unit_price": expected,
                }
            ],
            "total_amount": client_price,
            "consent_personal_data": True,
            "accept_price_changes": accept,
        }

    def test_unchanged_price_ok(self):
        resp = self.api.post("/api/v1/orders/", self._payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["total_amount"], "200.00")

    def test_price_changed_requires_accept(self):
        self.product.price = Decimal("250.00")
        self.product.save(update_fields=["price"])
        resp = self.api.post(
            "/api/v1/orders/", self._payload(expected="200.00"), format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("price_changed", str(resp.content))

    def test_accept_price_changes_creates_order(self):
        self.product.price = Decimal("250.00")
        self.product.save(update_fields=["price"])
        resp = self.api.post(
            "/api/v1/orders/",
            self._payload(expected="200.00", accept=True),
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["total_amount"], "250.00")

    def test_client_price_ignored(self):
        resp = self.api.post(
            "/api/v1/orders/", self._payload(client_price="1.00"), format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["total_amount"], "200.00")
