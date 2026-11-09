"""Защита полей 1С при PATCH и bulk prices."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.products.models import Category, Product

User = get_user_model()


@override_settings(ADMIN_OTP_ENABLED=False)
class OneCFieldProtectionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="79001112233", password="pass", is_staff=True, is_superuser=True
        )
        self.cat = Category.objects.create(title="C", slug="c-prot")
        self.product = Product.objects.create(
            title="Phone",
            slug="phone-prot",
            sku="SKU-1",
            onec_code="00-111",
            price=Decimal("1000.00"),
            category=self.cat,
        )
        self.local = Product.objects.create(
            title="Local",
            slug="local-prot",
            sku="SKU-L",
            price=Decimal("500.00"),
            category=self.cat,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_patch_price_blocked_for_onec_product(self):
        resp = self.client.patch(
            f"/api/v1/admin/products/{self.product.pk}/patch/",
            {"price": "999.00", "description": "ok"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("1000.00"))

    def test_patch_local_description_allowed(self):
        resp = self.client.patch(
            f"/api/v1/admin/products/{self.product.pk}/patch/",
            {"description": "локальное SEO"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.description, "локальное SEO")
        self.assertEqual(self.product.price, Decimal("1000.00"))

    def test_bulk_prices_skips_onec(self):
        resp = self.client.post(
            "/api/v1/admin/products/bulk/update-prices/",
            {
                "product_ids": [str(self.product.pk), str(self.local.pk)],
                "mode": "absolute",
                "value": 10,
                "direction": "increase",
                "field": "price",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["updated"], 1)
        self.assertEqual(resp.data["skipped_onec_managed"], 1)
        self.product.refresh_from_db()
        self.local.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("1000.00"))
        self.assertEqual(self.local.price, Decimal("510.00"))
