"""Новые заказы с bank_transfer отклоняются API (UI уже скрывает способ)."""

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
class BankTransferDisabledTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = CustomUser.objects.create_user(
            phone="79004441122", password="pass12345"
        )
        cat = Category.objects.create(title="C", slug="bt-c")
        self.product = Product.objects.create(
            title="P",
            slug="bt-p",
            price=Decimal("100.00"),
            category=cat,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="S", slug="bt-s", address="a", city="c", is_active=True
        )
        Stock.objects.create(
            product=self.product, store=self.store, quantity=5, reserved_quantity=0
        )
        self.api.force_authenticate(user=self.user)

    def test_bank_transfer_rejected(self):
        resp = self.api.post(
            "/api/v1/orders/",
            {
                "full_name": "Buyer",
                "phone": self.user.phone,
                "delivery_type": "pickup",
                "store": str(self.store.id),
                "payment_type": "bank_transfer",
                "items": [
                    {
                        "product_id": str(self.product.id),
                        "quantity": 1,
                        "price": "100.00",
                        "expected_unit_price": "100.00",
                    }
                ],
                "total_amount": "100.00",
                "consent_personal_data": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("payment_type", resp.json())
