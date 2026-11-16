"""
Fix-pack A (B8-001): гостевой cash/COD checkout не должен опираться на auth-only detail.
Backend контракт: guest create → guest_access_token; GET /orders/{id}/ — 401 анониму;
полные ПДн только через track/status с валидным guest_token.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings

from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Stock, Store


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
    ONE_C_API_ENABLED=False,
    ONE_C_ORDER_SYNC_ENABLED=False,
)
class FixPackAGuestSuccessContractTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        cat = Category.objects.create(title="FPA", slug="fpa-cat")
        self.product = Product.objects.create(
            title="FPA Phone",
            slug="fpa-phone",
            price=Decimal("1500.00"),
            category=cat,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="FPA Store",
            slug="fpa-store",
            address="a",
            city="Москва",
            is_active=True,
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            reserved_quantity=0,
            onec_series_id="",
        )

    def _create_guest(self, *, payment_type: str):
        payload = {
            "full_name": "Guest Buyer",
            "phone": "79005550101",
            "email": "guest@example.com",
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": payment_type,
            "items": [
                {
                    "product_id": str(self.product.id),
                    "quantity": 1,
                    "price": "1500.00",
                }
            ],
            "total_amount": "1500.00",
            "delivery_cost": "0",
            "bonus_used": "0",
            "consent_personal_data": True,
        }
        return self.api.post("/api/v1/orders/", payload, format="json")

    def test_guest_cash_create_returns_token_and_detail_requires_auth(self):
        resp = self._create_guest(payment_type="cash")
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        order_id = data["id"]
        token = data.get("guest_access_token")
        self.assertTrue(token)
        self.assertEqual(data["payment_type"], "cash")

        anon = self.api.get(f"/api/v1/orders/{order_id}/")
        self.assertEqual(anon.status_code, 401)

        limited = self.api.get(
            "/api/v1/orders/track/",
            {"order_number": data["order_number"], "phone": "79005550101"},
        )
        self.assertEqual(limited.status_code, 200)
        body = limited.json()
        self.assertTrue(body.get("guest_token_required"))
        self.assertNotIn("full_name", body)
        self.assertNotIn("items", body)

        full = self.api.get(
            "/api/v1/orders/track/",
            {
                "order_number": data["order_number"],
                "phone": "79005550101",
                "guest_token": token,
            },
        )
        self.assertEqual(full.status_code, 200)
        self.assertEqual(full.json()["full_name"], "Guest Buyer")
        self.assertEqual(len(full.json()["items"]), 1)

    def test_guest_card_on_delivery_same_guest_token_contract(self):
        resp = self._create_guest(payment_type="card_on_delivery")
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertTrue(data.get("guest_access_token"))
        self.assertEqual(
            self.api.get(f"/api/v1/orders/{data['id']}/").status_code,
            401,
        )

    def test_wrong_guest_token_does_not_reveal_pii(self):
        resp = self._create_guest(payment_type="cash")
        data = resp.json()
        bad = self.api.get(
            "/api/v1/orders/track/",
            {
                "order_number": data["order_number"],
                "phone": "79005550101",
                "guest_token": "not-the-real-token",
            },
        )
        self.assertEqual(bad.status_code, 200)
        body = bad.json()
        self.assertTrue(body.get("guest_token_required"))
        self.assertNotIn("full_name", body)
