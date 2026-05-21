"""
Unit-тесты для приложения products (задачи 1.2.5, 1.2.6, 1.2.7, 2.5.2, 2.5.3).
"""

from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Category, Product, ProductImage, ProductSpec
from .serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductImageSerializer,
    ProductSpecSerializer,
)


class TestCategorySerializer(TestCase):
    """Тесты CategorySerializer."""

    def test_serializer_fields(self):
        cat = Category.objects.create(
            title="Телефоны",
            slug="telefony",
            description="Смартфоны и телефоны",
        )
        data = CategorySerializer(cat).data
        self.assertEqual(data["id"], str(cat.id))
        self.assertEqual(data["title"], "Телефоны")
        self.assertEqual(data["slug"], "telefony")
        self.assertIsNone(data["parent"])
        self.assertEqual(data["description"], "Смартфоны и телефоны")

    def test_serializer_with_parent(self):
        parent = Category.objects.create(title="Электроника", slug="electronics")
        child = Category.objects.create(
            title="Ноутбуки",
            slug="laptops",
            parent=parent,
        )
        data = CategorySerializer(child).data
        self.assertEqual(str(data["parent"]), str(parent.id))


class TestProductImageSerializer(TestCase):
    """Тесты ProductImageSerializer."""

    def test_serializer_fields(self):
        category = Category.objects.create(title="Кат", slug="cat")
        product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=category,
        )
        # ProductImage требует image - используем временный файл или mock
        from django.core.files.uploadedfile import SimpleUploadedFile
        img = ProductImage.objects.create(
            product=product,
            image=SimpleUploadedFile("test.jpg", b"fake", content_type="image/jpeg"),
            is_main=True,
            alt_text="Тест",
        )
        data = ProductImageSerializer(img).data
        self.assertEqual(data["id"], str(img.id))
        self.assertTrue(data["is_main"])
        self.assertEqual(data["alt_text"], "Тест")
        self.assertIn("image", data)


class TestProductSpecSerializer(TestCase):
    """Тесты ProductSpecSerializer."""

    def test_serializer_fields(self):
        category = Category.objects.create(title="Кат", slug="cat")
        product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=category,
        )
        spec = ProductSpec.objects.create(
            product=product,
            name="Диагональ",
            value="15.6\"",
        )
        data = ProductSpecSerializer(spec).data
        self.assertEqual(data["name"], "Диагональ")
        self.assertEqual(data["value"], "15.6\"")


class TestProductListSerializer(TestCase):
    """Тесты ProductListSerializer."""

    def test_serializer_includes_main_image_and_discount(self):
        category = Category.objects.create(title="Кат", slug="cat")
        product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("80.00"),
            old_price=Decimal("100.00"),
            category=category,
        )
        data = ProductListSerializer(product).data
        self.assertEqual(data["id"], str(product.id))
        self.assertEqual(data["title"], "Товар")
        self.assertEqual(data["price"], "80.00")
        self.assertEqual(data["old_price"], "100.00")
        self.assertEqual(data["discount_percent"], 20.0)
        self.assertIn("category", data)
        self.assertEqual(data["category"]["slug"], "cat")
        self.assertIn("images", data)
        self.assertIsInstance(data["images"], list)

    def test_serializer_no_old_price_discount_zero(self):
        category = Category.objects.create(title="Кат", slug="cat")
        product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=category,
        )
        data = ProductListSerializer(product).data
        self.assertEqual(data["discount_percent"], 0)


class TestProductDetailSerializer(TestCase):
    """Тесты ProductDetailSerializer."""

    def test_serializer_includes_images_specs_category_discount(self):
        category = Category.objects.create(title="Кат", slug="cat")
        product = Product.objects.create(
            title="Товар",
            slug="product",
            description="Описание",
            price=Decimal("50.00"),
            old_price=Decimal("100.00"),
            category=category,
            brand="Бренд",
        )
        ProductSpec.objects.create(product=product, name="Цвет", value="Чёрный")
        data = ProductDetailSerializer(product).data
        self.assertEqual(data["title"], "Товар")
        self.assertEqual(data["description"], "Описание")
        self.assertEqual(data["discount_percent"], 50.0)
        self.assertEqual(data["category"]["title"], "Кат")
        self.assertIn("images", data)
        self.assertIn("specs", data)
        self.assertEqual(len(data["specs"]), 1)
        self.assertEqual(data["specs"][0]["name"], "Цвет")
        self.assertEqual(data["specs"][0]["value"], "Чёрный")

    def test_serializer_includes_stock_and_is_in_user_cart(self):
        category = Category.objects.create(title="Кат", slug="cat")
        product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=category,
        )
        data = ProductDetailSerializer(product).data
        self.assertIn("stock", data)
        self.assertIsInstance(data["stock"], list)
        self.assertIn("is_in_user_cart", data)
        self.assertFalse(data["is_in_user_cart"])


# --- API tests (1.2.6, 1.2.7) ---


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False})
class TestCategoryViewSet(TestCase):
    """Тесты CategoryViewSet: list, retrieve, фильтр is_active, пагинация."""

    def setUp(self):
        self.client = APIClient()
        self.cat_active = Category.objects.create(
            title="Активная",
            slug="active",
            is_active=True,
        )
        self.cat_inactive = Category.objects.create(
            title="Неактивная",
            slug="inactive",
            is_active=False,
        )

    def test_list_returns_only_active_by_default(self):
        url = reverse("api_v1:products:category-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        slugs = [c["slug"] for c in data["results"]]
        self.assertIn("active", slugs)
        self.assertNotIn("inactive", slugs)

    def test_list_filter_is_active_false(self):
        url = reverse("api_v1:products:category-list")
        response = self.client.get(url, {"is_active": "false"})
        self.assertEqual(response.status_code, 200)
        slugs = [c["slug"] for c in response.json()["results"]]
        self.assertIn("inactive", slugs)

    def test_retrieve_category(self):
        url = reverse(
            "api_v1:products:category-detail",
            kwargs={"pk": self.cat_active.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], "active")

    def test_list_paginated(self):
        url = reverse("api_v1:products:category-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False})
class TestProductListView(TestCase):
    """Тесты ProductListView: фильтры, сортировка, пагинация."""

    def setUp(self):
        self.client = APIClient()
        self.cat = Category.objects.create(title="Кат", slug="cat")
        self.p1 = Product.objects.create(
            title="Товар Дорогой",
            slug="product-1",
            price=Decimal("100.00"),
            category=self.cat,
            is_active=True,
        )
        self.p2 = Product.objects.create(
            title="Товар Дешёвый",
            slug="product-2",
            price=Decimal("50.00"),
            category=self.cat,
            is_active=True,
        )

    def test_list_returns_products(self):
        url = reverse("api_v1:products:product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        slugs = [p["slug"] for p in data["results"]]
        self.assertIn("product-1", slugs)
        self.assertIn("product-2", slugs)

    def test_list_filter_by_category(self):
        other_cat = Category.objects.create(title="Другая", slug="other")
        Product.objects.create(
            title="Чужой",
            slug="other-product",
            price=Decimal("10.00"),
            category=other_cat,
            is_active=True,
        )
        url = reverse("api_v1:products:product-list")
        response = self.client.get(url, {"category": "cat"})
        self.assertEqual(response.status_code, 200)
        slugs = [p["slug"] for p in response.json()["results"]]
        self.assertIn("product-1", slugs)
        self.assertNotIn("other-product", slugs)

    def test_list_filter_min_max_price(self):
        url = reverse("api_v1:products:product-list")
        response = self.client.get(url, {"min_price": "60", "max_price": "90"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 0)
        response = self.client.get(url, {"min_price": "40", "max_price": "60"})
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["slug"], "product-2")

    def test_list_search(self):
        url = reverse("api_v1:products:product-list")
        response = self.client.get(url, {"search": "Дорогой"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["slug"], "product-1")

    def test_list_ordering_price_asc(self):
        url = reverse("api_v1:products:product-list")
        response = self.client.get(url, {"ordering": "price_asc"})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(results[0]["slug"], "product-2")
        self.assertEqual(results[1]["slug"], "product-1")


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False})
class TestProductDetailView(TestCase):
    """Тесты ProductDetailView: retrieve по slug, поля stock и is_in_user_cart."""

    def setUp(self):
        self.client = APIClient()
        self.cat = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="my-product",
            price=Decimal("99.00"),
            category=self.cat,
            is_active=True,
        )

    def test_retrieve_by_slug(self):
        url = reverse(
            "api_v1:products:product-detail",
            kwargs={"slug": self.product.slug},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], "my-product")
        self.assertIn("images", data)
        self.assertIn("specs", data)
        self.assertIn("stock", data)
        self.assertIn("is_in_user_cart", data)
        self.assertFalse(data["is_in_user_cart"])

    def test_retrieve_404_for_inactive(self):
        self.product.is_active = False
        self.product.save()
        url = reverse(
            "api_v1:products:product-detail",
            kwargs={"slug": self.product.slug},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestProductListCaching(TestCase):
    """Тесты кэширования списка товаров (задача 2.5.2)."""

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        self.cat = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=self.cat,
        )

    def test_list_response_cached(self):
        url = reverse("api_v1:products:product-list")
        r1 = self.client.get(url)
        r2 = self.client.get(url)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json(), r2.json())

    def test_list_invalidated_on_product_save(self):
        url = reverse("api_v1:products:product-list")
        self.client.get(url)
        Product.objects.create(
            title="Новый товар",
            slug="new-product",
            price=Decimal("200.00"),
            category=self.cat,
        )
        response = self.client.get(url)
        results = response.json().get("results", [])
        slugs = [p["slug"] for p in results]
        self.assertIn("new-product", slugs)

    def test_cache_key_depends_on_filters(self):
        Product.objects.create(
            title="Дешёвый",
            slug="cheap",
            price=Decimal("50.00"),
            category=self.cat,
        )
        url = reverse("api_v1:products:product-list")
        r1 = self.client.get(url, {"ordering": "price_asc"})
        r2 = self.client.get(url, {"ordering": "price_desc"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json()["results"][0]["slug"], "cheap")
        self.assertEqual(r2.json()["results"][0]["slug"], "product")


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestCategoryListCaching(TestCase):
    """Тесты кэширования списка категорий (задача 2.5.3)."""

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        Category.objects.create(title="Кат1", slug="cat1")

    def test_category_list_response_cached(self):
        url = reverse("api_v1:products:category-list")
        r1 = self.client.get(url)
        r2 = self.client.get(url)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json(), r2.json(), "Ответ списка категорий должен отдаваться из кэша")

    def test_category_list_invalidated_on_category_save(self):
        url = reverse("api_v1:products:category-list")
        self.client.get(url)
        Category.objects.create(title="Кат2", slug="cat2")
        response = self.client.get(url)
        data = response.json()
        results = data["results"] if "results" in data else data
        titles = [c["title"] for c in results]
        self.assertIn("Кат2", titles)
