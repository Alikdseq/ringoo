"""
Admin API: DELETE для product images / specs / store images (ранее 405).
"""

import uuid
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from rest_framework.test import APIClient

from apps.admin_api.permissions import (
    RINGOO_GROUP_CATALOG,
    RINGOO_GROUP_ORDERS,
    RINGOO_GROUP_STORES,
)
from apps.products.models import Category, Product, ProductImage, ProductSpec
from apps.stores.models import Store, StoreImage
from apps.users.models import CustomUser


def _tiny_jpeg():
    return SimpleUploadedFile("test.jpg", b"fake-image-bytes", content_type="image/jpeg")


@override_settings(ADMIN_OTP_ENABLED=False)
class AdminProductImageSpecDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Group.objects.get_or_create(name=RINGOO_GROUP_CATALOG)
        Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
        Group.objects.get_or_create(name=RINGOO_GROUP_STORES)

        self.catalog_staff = CustomUser.objects.create_user(
            phone="79001110001",
            password="pass12345",
            is_staff=True,
        )
        self.catalog_staff.groups.add(Group.objects.get(name=RINGOO_GROUP_CATALOG))

        self.orders_staff = CustomUser.objects.create_user(
            phone="79001110002",
            password="pass12345",
            is_staff=True,
        )
        self.orders_staff.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))

        self.stores_staff = CustomUser.objects.create_user(
            phone="79001110003",
            password="pass12345",
            is_staff=True,
        )
        self.stores_staff.groups.add(Group.objects.get(name=RINGOO_GROUP_STORES))

        self.category = Category.objects.create(
            title="Cat",
            slug="cat-delete-test",
            is_active=True,
        )
        self.product = Product.objects.create(
            title="Phone",
            slug="phone-delete-test",
            price=Decimal("1000.00"),
            category=self.category,
            is_active=True,
        )
        self.image = ProductImage.objects.create(
            product=self.product,
            image=_tiny_jpeg(),
            is_main=True,
            sort_order=0,
        )
        self.spec = ProductSpec.objects.create(
            product=self.product,
            name="Color",
            value="Black",
            sort_order=0,
        )
        self.store = Store.objects.create(
            name="Store A",
            slug="store-a-delete-test",
            city="Moscow",
            address="Lenina 1",
            is_active=True,
        )
        self.store_image = StoreImage.objects.create(
            store=self.store,
            image=_tiny_jpeg(),
            sort_order=0,
        )

    def test_delete_product_image_returns_204_and_removes_row(self):
        image_id = self.image.pk
        self.client.force_authenticate(self.catalog_staff)
        resp = self.client.delete(f"/api/v1/admin/products/images/{image_id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(ProductImage.objects.filter(pk=image_id).exists())

    def test_delete_product_image_missing_uuid_404(self):
        self.client.force_authenticate(self.catalog_staff)
        missing = uuid.uuid4()
        resp = self.client.delete(f"/api/v1/admin/products/images/{missing}/")
        self.assertEqual(resp.status_code, 404)

    def test_delete_product_image_forbidden_without_catalog_group(self):
        image_id = self.image.pk
        self.client.force_authenticate(self.orders_staff)
        resp = self.client.delete(f"/api/v1/admin/products/images/{image_id}/")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ProductImage.objects.filter(pk=image_id).exists())

    def test_patch_product_image_still_works(self):
        self.client.force_authenticate(self.catalog_staff)
        resp = self.client.patch(
            f"/api/v1/admin/products/images/{self.image.pk}/",
            {"alt_text": "updated-alt"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.image.refresh_from_db()
        self.assertEqual(self.image.alt_text, "updated-alt")

    def test_delete_product_spec_returns_204_and_removes_row(self):
        spec_id = self.spec.pk
        self.client.force_authenticate(self.catalog_staff)
        resp = self.client.delete(f"/api/v1/admin/products/specs/{spec_id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(ProductSpec.objects.filter(pk=spec_id).exists())

    def test_delete_product_spec_missing_uuid_404(self):
        self.client.force_authenticate(self.catalog_staff)
        resp = self.client.delete(f"/api/v1/admin/products/specs/{uuid.uuid4()}/")
        self.assertEqual(resp.status_code, 404)

    def test_delete_product_spec_forbidden_without_catalog_group(self):
        spec_id = self.spec.pk
        self.client.force_authenticate(self.orders_staff)
        resp = self.client.delete(f"/api/v1/admin/products/specs/{spec_id}/")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ProductSpec.objects.filter(pk=spec_id).exists())

    def test_patch_product_spec_still_works(self):
        self.client.force_authenticate(self.catalog_staff)
        resp = self.client.patch(
            f"/api/v1/admin/products/specs/{self.spec.pk}/",
            {"value": "White"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.spec.refresh_from_db()
        self.assertEqual(self.spec.value, "White")

    def test_delete_store_image_returns_204_and_removes_row(self):
        image_id = self.store_image.pk
        self.client.force_authenticate(self.stores_staff)
        resp = self.client.delete(f"/api/v1/admin/stores/images/{image_id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(StoreImage.objects.filter(pk=image_id).exists())

    def test_delete_store_image_missing_uuid_404(self):
        self.client.force_authenticate(self.stores_staff)
        resp = self.client.delete(f"/api/v1/admin/stores/images/{uuid.uuid4()}/")
        self.assertEqual(resp.status_code, 404)

    def test_delete_store_image_forbidden_without_stores_group(self):
        image_id = self.store_image.pk
        self.client.force_authenticate(self.catalog_staff)
        resp = self.client.delete(f"/api/v1/admin/stores/images/{image_id}/")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(StoreImage.objects.filter(pk=image_id).exists())

    def test_patch_store_image_still_works(self):
        self.client.force_authenticate(self.stores_staff)
        resp = self.client.patch(
            f"/api/v1/admin/stores/images/{self.store_image.pk}/",
            {"alt_text": "store-alt"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.store_image.refresh_from_db()
        self.assertEqual(self.store_image.alt_text, "store-alt")
