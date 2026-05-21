"""
Тесты избранного: изоляция данных по пользователю (регресс IDOR).
"""

from decimal import Decimal

from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.users.models import CustomUser
from apps.wishlist.models import WishlistItem


class TestWishlistIsolation(TestCase):
    def setUp(self):
        self.client = APIClient()
        cat = Category.objects.create(title="К", slug="c-wish")
        self.product = Product.objects.create(
            title="P",
            slug="p-wish",
            price=Decimal("10.00"),
            category=cat,
            is_active=True,
        )
        self.user_a = CustomUser.objects.create_user(
            phone="79991110001", password="pw12345678", email="a@t.com"
        )
        self.user_b = CustomUser.objects.create_user(
            phone="79991110002", password="pw12345678", email="b@t.com"
        )

    def test_user_sees_only_own_wishlist(self):
        WishlistItem.objects.create(user=self.user_a, product=self.product)
        url = reverse("api_v1:wishlist:wishlist-list")
        self.client.force_authenticate(user=self.user_b)
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json(), [])

    def test_delete_only_removes_own_row(self):
        WishlistItem.objects.create(user=self.user_a, product=self.product)
        url = reverse(
            "api_v1:wishlist:wishlist-item-detail",
            kwargs={"product_id": self.product.id},
        )
        self.client.force_authenticate(user=self.user_b)
        r = self.client.delete(url)
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            WishlistItem.objects.filter(
                user=self.user_a, product=self.product
            ).exists()
        )
