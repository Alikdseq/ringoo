"""SEC-005: X-Idempotency-Key изолирован между клиентами."""

from __future__ import annotations

from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec005-idem",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec005-sess",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
    ORDER_IDEMPOTENCY_CACHE_TIMEOUT=3600,
)
class Sec005OrderIdempotencyIsolationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()
        cat = Category.objects.create(title="C", slug=f"sec5-{Category.objects.count()}")
        self.product = Product.objects.create(
            title="P",
            slug=f"sec5-p-{Product.objects.count()}",
            price=Decimal("100.00"),
            category=cat,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="S",
            slug=f"sec5-s-{Store.objects.count()}",
            address="a",
            city="Москва",
            is_active=True,
        )
        Stock.objects.create(
            product=self.product, store=self.store, quantity=50, reserved_quantity=0
        )
        self.user_a = CustomUser.objects.create_user(
            phone="79005110001", password="pass12345"
        )
        self.user_b = CustomUser.objects.create_user(
            phone="79005110002", password="pass12345"
        )

    def _payload(self, *, phone: str, name: str = "Buyer"):
        return {
            "full_name": name,
            "phone": phone,
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": "cash",
            "items": [
                {
                    "product_id": str(self.product.id),
                    "quantity": 1,
                    "price": "100.00",
                }
            ],
            "total_amount": "100.00",
            "delivery_cost": "0",
            "bonus_used": "0",
            "consent_personal_data": True,
        }

    def test_same_user_same_key_returns_same_order(self):
        self.api.force_authenticate(user=self.user_a)
        headers = {"HTTP_X_IDEMPOTENCY_KEY": "same-key-user-a"}
        r1 = self.api.post(
            "/api/v1/orders/",
            self._payload(phone=self.user_a.phone, name="A1"),
            format="json",
            **headers,
        )
        self.assertEqual(r1.status_code, 201, r1.content)
        r2 = self.api.post(
            "/api/v1/orders/",
            self._payload(phone=self.user_a.phone, name="A2"),
            format="json",
            **headers,
        )
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.json()["id"], r2.json()["id"])
        self.assertEqual(
            Order.objects.filter(user=self.user_a).count(),
            1,
        )

    def test_different_users_same_key_isolated(self):
        key = "shared-cross-user-key"
        self.api.force_authenticate(user=self.user_a)
        r1 = self.api.post(
            "/api/v1/orders/",
            self._payload(phone=self.user_a.phone, name="Alice"),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r1.status_code, 201, r1.content)

        self.api.force_authenticate(user=self.user_b)
        r2 = self.api.post(
            "/api/v1/orders/",
            self._payload(phone=self.user_b.phone, name="Bob"),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r2.status_code, 201, r2.content)
        self.assertNotEqual(r1.json()["id"], r2.json()["id"])
        self.assertEqual(r1.json()["full_name"], "Alice")
        self.assertEqual(r2.json()["full_name"], "Bob")

    def test_different_guests_same_key_isolated(self):
        key = "guest-shared-key"
        client1 = APIClient()
        client2 = APIClient()
        # Разные session cookie
        session1 = client1.session
        session1.save()
        session2 = client2.session
        session2.save()
        self.assertNotEqual(session1.session_key, session2.session_key)

        r1 = client1.post(
            "/api/v1/orders/",
            self._payload(phone="79005120001", name="Guest1"),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        r2 = client2.post(
            "/api/v1/orders/",
            self._payload(phone="79005120002", name="Guest2"),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r1.status_code, 201, r1.content)
        self.assertEqual(r2.status_code, 201, r2.content)
        self.assertNotEqual(r1.json()["id"], r2.json()["id"])

    def test_guest_repeat_same_session_dedupes(self):
        key = "guest-repeat"
        client = APIClient()
        session = client.session
        session.save()
        payload = self._payload(phone="79005120003", name="GuestR")
        r1 = client.post(
            "/api/v1/orders/", payload, format="json", HTTP_X_IDEMPOTENCY_KEY=key
        )
        r2 = client.post(
            "/api/v1/orders/", payload, format="json", HTTP_X_IDEMPOTENCY_KEY=key
        )
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.json()["id"], r2.json()["id"])
        self.assertEqual(Order.objects.filter(phone="79005120003").count(), 1)

    def test_different_keys_create_two_orders(self):
        self.api.force_authenticate(user=self.user_a)
        r1 = self.api.post(
            "/api/v1/orders/",
            self._payload(phone=self.user_a.phone),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="key-one",
        )
        r2 = self.api.post(
            "/api/v1/orders/",
            self._payload(phone=self.user_a.phone),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="key-two",
        )
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertNotEqual(r1.json()["id"], r2.json()["id"])

    def test_ttl_expiry_allows_new_order(self):
        self.api.force_authenticate(user=self.user_a)
        key = "ttl-key"
        r1 = self.api.post(
            "/api/v1/orders/",
            self._payload(phone=self.user_a.phone),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r1.status_code, 201)
        cache.clear()
        r2 = self.api.post(
            "/api/v1/orders/",
            self._payload(phone=self.user_a.phone),
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r2.status_code, 201)
        self.assertNotEqual(r1.json()["id"], r2.json()["id"])
