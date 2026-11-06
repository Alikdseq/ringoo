"""SEC-002: публичные отзывы — только approved, без email."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.admin_api.permissions import RINGOO_GROUP_CONTENT
from apps.content.models import Review
from apps.products.models import Category, Product
from apps.users.models import CustomUser


@override_settings(
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
    ADMIN_OTP_ENABLED=False,
)
class Sec002PublicReviewsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(title="Cat", slug="sec2-cat")
        self.product = Product.objects.create(
            title="P",
            slug="sec2-p",
            price=Decimal("10"),
            category=self.category,
            is_active=True,
        )
        self.approved = Review.objects.create(
            product=self.product,
            name="Ann",
            email="ann@example.com",
            rating=5,
            comment="Great",
            is_approved=True,
        )
        self.pending = Review.objects.create(
            product=self.product,
            name="Bob",
            email="bob@example.com",
            rating=1,
            comment="Bad draft",
            is_approved=False,
        )
        self.url = reverse("api_v1:content:review-list")

    def test_anon_sees_only_approved(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", resp.json())
        ids = {r["id"] for r in results}
        self.assertIn(str(self.approved.id), ids)
        self.assertNotIn(str(self.pending.id), ids)

    def test_is_approved_false_does_not_leak(self):
        resp = self.client.get(self.url, {"is_approved": "false"})
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", resp.json())
        ids = {r["id"] for r in results}
        self.assertNotIn(str(self.pending.id), ids)
        self.assertIn(str(self.approved.id), ids)

    def test_is_approved_true_safe(self):
        resp = self.client.get(self.url, {"is_approved": "true"})
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", resp.json())
        self.assertTrue(all(r.get("is_approved") for r in results))

    def test_invalid_is_approved_param_safe(self):
        resp = self.client.get(self.url, {"is_approved": "maybe"})
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", resp.json())
        ids = {r["id"] for r in results}
        self.assertNotIn(str(self.pending.id), ids)

    def test_product_filter_keeps_approved_only(self):
        other = Product.objects.create(
            title="P2",
            slug="sec2-p2",
            price=Decimal("11"),
            category=self.category,
            is_active=True,
        )
        Review.objects.create(
            product=other,
            name="X",
            email="x@example.com",
            rating=3,
            comment="other",
            is_approved=True,
        )
        resp = self.client.get(self.url, {"product": str(self.product.id)})
        results = resp.json().get("results", resp.json())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.approved.id))

    def test_public_response_has_no_email(self):
        resp = self.client.get(self.url)
        results = resp.json().get("results", resp.json())
        for item in results:
            self.assertNotIn("email", item)
        self.assertNotIn("ann@example.com", resp.content.decode())

    def test_pagination_does_not_leak_pending(self):
        for i in range(25):
            Review.objects.create(
                product=self.product,
                name=f"N{i}",
                email=f"n{i}@ex.com",
                rating=4,
                comment=f"c{i}",
                is_approved=True,
            )
            Review.objects.create(
                product=self.product,
                name=f"H{i}",
                email=f"h{i}@ex.com",
                rating=1,
                comment=f"hidden{i}",
                is_approved=False,
            )
        resp = self.client.get(self.url, {"page": 1})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        results = body.get("results", body)
        self.assertTrue(all(r.get("is_approved") for r in results))
        raw = resp.content.decode()
        self.assertNotIn("h0@ex.com", raw)

    def test_admin_list_can_see_email_and_pending(self):
        Group.objects.get_or_create(name=RINGOO_GROUP_CONTENT)
        staff = CustomUser.objects.create_user(
            phone="79002220001", password="pass12345", is_staff=True
        )
        staff.groups.add(Group.objects.get(name=RINGOO_GROUP_CONTENT))
        self.client.force_authenticate(user=staff)
        resp = self.client.get(
            "/api/v1/admin/content/reviews/", {"is_approved": "false"}
        )
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", resp.json())
        ids = {r["id"] for r in results}
        self.assertIn(str(self.pending.id), ids)
        pending_row = next(r for r in results if r["id"] == str(self.pending.id))
        self.assertEqual(pending_row.get("email"), "bob@example.com")
