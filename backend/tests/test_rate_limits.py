"""
§10.2.3: проверка срабатывания DRF throttling при реальных лимитах.

В test settings auth_* ослаблены и default cache — DummyCache; здесь включаем locmem + низкие лимиты.
"""

from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser


def _rest_framework_with_rates(**rate_overrides):
    rf = dict(settings.REST_FRAMEWORK)
    rates = dict(rf.get("DEFAULT_THROTTLE_RATES") or {})
    rates.update(rate_overrides)
    rf["DEFAULT_THROTTLE_RATES"] = rates
    return rf


_THROTTLE_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "sessions": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}


@override_settings(
    CACHES=_THROTTLE_CACHES,
    REST_FRAMEWORK=_rest_framework_with_rates(auth_login="2/minute"),
)
class TestAuthLoginThrottle(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        CustomUser.objects.create_user("79990001111", password="correctpass12")

    def test_login_throttle_returns_429_after_limit(self):
        url = "/api/v1/auth/token/"
        for _ in range(2):
            r = self.client.post(
                url,
                {"username": "79990001111", "password": "wrongpass"},
                format="json",
            )
            self.assertEqual(r.status_code, 401, r.content)
        r3 = self.client.post(
            url,
            {"username": "79990001111", "password": "wrongpass"},
            format="json",
        )
        self.assertEqual(r3.status_code, 429, r3.content)


@override_settings(
    CACHES=_THROTTLE_CACHES,
    REST_FRAMEWORK=_rest_framework_with_rates(auth_refresh="2/minute"),
)
class TestAuthRefreshThrottle(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_refresh_throttle_returns_429_after_limit(self):
        url = "/api/v1/auth/token/refresh/"
        for _ in range(2):
            r = self.client.post(url, {"refresh": "not-a-valid-token"}, format="json")
            self.assertIn(r.status_code, (401, 400), r.content)
        r3 = self.client.post(url, {"refresh": "not-a-valid-token"}, format="json")
        self.assertEqual(r3.status_code, 429, r3.content)


@override_settings(
    CACHES=_THROTTLE_CACHES,
    REST_FRAMEWORK=_rest_framework_with_rates(order_create_anon="2/minute"),
)
class TestOrderCreateAnonThrottle(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.category = Category.objects.create(title="Кат", slug="cat-th")
        self.product = Product.objects.create(
            title="Товар",
            slug="product-th",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="М",
            slug="m-th",
            address="А",
            city="Москва",
            is_active=True,
        )
        Stock.objects.create(product=self.product, store=self.store, quantity=50)

    def _payload(self):
        return {
            "full_name": "Иван",
            "phone": "+79991234567",
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "100.00"}
            ],
            "total_amount": "100.00",
            "consent_personal_data": True,
        }

    def test_anon_order_post_throttle_429(self):
        url = reverse("api_v1:orders:order-list-create")
        for _ in range(2):
            r = self.client.post(url, self._payload(), format="json")
            self.assertEqual(r.status_code, 201, r.content)
        r3 = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r3.status_code, 429, r3.content)


@override_settings(
    CACHES=_THROTTLE_CACHES,
    REST_FRAMEWORK=_rest_framework_with_rates(order_create="2/minute"),
)
class TestOrderCreateUserThrottle(TransactionTestCase):
    """Лимит создания заказа для авторизованного пользователя."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            "79990002222", password="userpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(title="Кат2", slug="cat-th2")
        self.product = Product.objects.create(
            title="Товар2",
            slug="product-th2",
            price=Decimal("50.00"),
            category=self.category,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="М2",
            slug="m-th2",
            address="А",
            city="Москва",
            is_active=True,
        )
        Stock.objects.create(product=self.product, store=self.store, quantity=50)

    def _payload(self):
        return {
            "full_name": "Иван",
            "phone": "+79991234567",
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": "cash",
            "items": [
                {"product_id": str(self.product.id), "quantity": 1, "price": "50.00"}
            ],
            "total_amount": "50.00",
            "consent_personal_data": True,
        }

    def test_user_order_post_throttle_429(self):
        url = reverse("api_v1:orders:order-list-create")
        for _ in range(2):
            r = self.client.post(url, self._payload(), format="json")
            self.assertEqual(r.status_code, 201, r.content)
        r3 = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r3.status_code, 429, r3.content)
