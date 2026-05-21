"""
Unit-тесты промокодов: сервис (2.3.3), API (2.3.4).
"""

from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import PromoCode
from .services import apply_promo_code


def _now():
    return timezone.now()


class TestApplyPromoCode(TestCase):
    """Тесты apply_promo_code (задача 2.3.3)."""

    def setUp(self):
        self.valid_from = _now() - timezone.timedelta(days=1)
        self.valid_until = _now() + timezone.timedelta(days=1)

    def test_valid_percent_discount(self):
        PromoCode.objects.create(
            code="SALE10",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("10"),
            start_date=self.valid_from,
            end_date=self.valid_until,
        )
        result = apply_promo_code("sale10", Decimal("1000"))
        self.assertEqual(result, Decimal("100.00"))

    def test_valid_fixed_discount(self):
        PromoCode.objects.create(
            code="FIX100",
            discount_type=PromoCode.DISCOUNT_FIXED,
            discount_value=Decimal("100"),
            start_date=self.valid_from,
            end_date=self.valid_until,
        )
        result = apply_promo_code("  fix100  ", Decimal("500"))
        self.assertEqual(result, Decimal("100.00"))

    def test_fixed_discount_capped_by_order_amount(self):
        PromoCode.objects.create(
            code="FIX500",
            discount_type=PromoCode.DISCOUNT_FIXED,
            discount_value=Decimal("500"),
            start_date=self.valid_from,
            end_date=self.valid_until,
        )
        result = apply_promo_code("FIX500", Decimal("300"))
        self.assertEqual(result, Decimal("300.00"))

    def test_nonexistent_code_returns_none(self):
        result = apply_promo_code("NOSUCH", Decimal("100"))
        self.assertIsNone(result)

    def test_empty_code_returns_none(self):
        result = apply_promo_code("", Decimal("100"))
        self.assertIsNone(result)
        result = apply_promo_code("   ", Decimal("100"))
        self.assertIsNone(result)

    def test_min_order_amount_not_met_returns_none(self):
        PromoCode.objects.create(
            code="MIN500",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("5"),
            min_order_amount=Decimal("500"),
            start_date=self.valid_from,
            end_date=self.valid_until,
        )
        result = apply_promo_code("MIN500", Decimal("300"))
        self.assertIsNone(result)

    def test_min_order_amount_met_returns_discount(self):
        PromoCode.objects.create(
            code="MIN500",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("10"),
            min_order_amount=Decimal("500"),
            start_date=self.valid_from,
            end_date=self.valid_until,
        )
        result = apply_promo_code("MIN500", Decimal("600"))
        self.assertEqual(result, Decimal("60.00"))

    def test_expired_code_returns_none(self):
        past_start = _now() - timezone.timedelta(days=2)
        past_end = _now() - timezone.timedelta(hours=1)
        PromoCode.objects.create(
            code="EXPIRED",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("5"),
            start_date=past_start,
            end_date=past_end,
        )
        result = apply_promo_code("EXPIRED", Decimal("100"))
        self.assertIsNone(result)

    def test_max_uses_exceeded_returns_none(self):
        PromoCode.objects.create(
            code="LIMIT1",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("5"),
            max_uses=1,
            used_count=1,
            start_date=self.valid_from,
            end_date=self.valid_until,
        )
        result = apply_promo_code("LIMIT1", Decimal("100"))
        self.assertIsNone(result)

    def test_inactive_code_returns_none(self):
        PromoCode.objects.create(
            code="OFF",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("5"),
            is_active=False,
            start_date=self.valid_from,
            end_date=self.valid_until,
        )
        result = apply_promo_code("OFF", Decimal("100"))
        self.assertIsNone(result)


@override_settings(
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False}
)
class TestPromoCodeValidateAPI(TestCase):
    """Тесты API валидации промокода (задача 2.3.4)."""

    def setUp(self):
        self.client = APIClient()
        self.valid_from = _now() - timezone.timedelta(days=1)
        self.valid_until = _now() + timezone.timedelta(days=1)

    def test_validate_success(self):
        PromoCode.objects.create(
            code="API10",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("10"),
            start_date=self.valid_from,
            end_date=self.valid_until,
        )
        url = reverse("api_v1:promocodes:validate")
        response = self.client.post(
            url,
            {"code": "api10", "order_amount": "1000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["discount"], "100.00")

    def test_validate_invalid_code_400(self):
        url = reverse("api_v1:promocodes:validate")
        response = self.client.post(
            url,
            {"code": "INVALID", "order_amount": "1000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.json())

    def test_validate_missing_params_400(self):
        url = reverse("api_v1:promocodes:validate")
        response = self.client.post(url, {"code": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(url, {"order_amount": "100"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
