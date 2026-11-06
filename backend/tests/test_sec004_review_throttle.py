"""SEC-004: отдельный throttle на создание отзывов."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.products.models import Category, Product


_REST = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/hour",
        "user": "10000/hour",
        "anon_read": "10000/hour",
        "user_read": "10000/hour",
        "review_create_anon": "3/hour",
        "review_create": "3/hour",
    },
}


@override_settings(
    REST_FRAMEWORK=_REST,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec004-throttle",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec004-sessions",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class Sec004ReviewCreateThrottleTests(TestCase):
    def setUp(self):
        from django.core.cache import caches

        caches["default"].clear()
        self.client = APIClient()
        cat = Category.objects.create(
            title="C", slug=f"sec4-c-{Category.objects.count()}"
        )
        self.product = Product.objects.create(
            title="P",
            slug=f"sec4-p-{Product.objects.count()}",
            price=Decimal("10"),
            category=cat,
            is_active=True,
        )
        self.url = reverse("api_v1:content:review-list")

    def _payload(self, i: int):
        return {
            "product": str(self.product.id),
            "name": f"Guest{i}",
            "email": f"g{i}@test.com",
            "rating": 5,
            "comment": f"Comment number {i}",
        }

    def test_within_limit_ok_then_429(self):
        for i in range(3):
            resp = self.client.post(self.url, self._payload(i), format="json")
            self.assertEqual(resp.status_code, 201, resp.content)
        blocked = self.client.post(self.url, self._payload(99), format="json")
        self.assertEqual(blocked.status_code, 429)

    def test_list_not_blocked_by_create_scope(self):
        for i in range(3):
            self.client.post(self.url, self._payload(i), format="json")
        # create limit исчерпан
        self.assertEqual(
            self.client.post(self.url, self._payload(50), format="json").status_code,
            429,
        )
        # чтение всё ещё доступно
        listing = self.client.get(self.url)
        self.assertEqual(listing.status_code, 200)
