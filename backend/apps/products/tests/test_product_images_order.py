from decimal import Decimal

from django.test import TestCase

from apps.products.models import Category, Product, ProductColor, ProductImage
from apps.products.serializers import ProductListSerializer
from apps.products.services.product_images import ordered_product_images


class TestOrderedProductImages(TestCase):
    def test_all_images_per_color_in_api_order(self):
        cat = Category.objects.create(title="Samsung", slug="samsung")
        product = Product.objects.create(
            title="Galaxy S26",
            slug="galaxy-s26-test",
            price=Decimal("100000"),
            category=cat,
            brand="Samsung",
        )
        black = ProductColor.objects.create(
            product=product, slug="black", label="Black", sort_order=0, is_active=True
        )
        sky = ProductColor.objects.create(
            product=product, slug="skyblue", label="SkyBlue", sort_order=1, is_active=True
        )
        for i, col in enumerate((black, sky)):
            for j in range(4):
                ProductImage.objects.create(
                    product=product,
                    color=col,
                    is_main=j == 0,
                    sort_order=i * 10 + j,
                )

        ordered = ordered_product_images(product)
        self.assertEqual(len(ordered), 8)
        self.assertTrue(all(img.color_id == black.id for img in ordered[:4]))
        self.assertTrue(all(img.color_id == sky.id for img in ordered[4:]))

        data = ProductListSerializer(product).data
        self.assertEqual(len(data["images"]), 8)
