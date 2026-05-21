"""
Unit-тесты приложения stores (задачи 1.3.3, 1.3.4).
"""

from decimal import Decimal

from django.db import transaction
from django.test import TestCase
from django.urls import reverse

from apps.products.models import Category, Product
from rest_framework.test import APIClient

from .models import Store, Stock
from .serializers import StockSerializer, StoreSerializer


# --- Сериализаторы (1.3.3) ---


class TestStoreSerializer(TestCase):
    def test_store_serializer_fields(self):
        store = Store.objects.create(
            name="Магазин 1",
            slug="store-1",
            address="ул. Ленина 1",
            city="Москва",
            phone="+79991234567",
            working_hours={"monday": "9:00-21:00"},
        )
        data = StoreSerializer(store).data
        self.assertEqual(data["id"], str(store.id))
        self.assertEqual(data["name"], "Магазин 1")
        self.assertEqual(data["slug"], "store-1")
        self.assertEqual(data["city"], "Москва")
        self.assertIsNone(data["coordinates"])

    def test_store_serializer_coordinates(self):
        store = Store.objects.create(
            name="Магазин 2",
            slug="store-2",
            address="ул. Пушкина 2",
            city="СПб",
            latitude=Decimal("55.755826"),
            longitude=Decimal("37.617299"),
        )
        data = StoreSerializer(store).data
        self.assertEqual(data["coordinates"]["latitude"], "55.755826")
        self.assertEqual(data["coordinates"]["longitude"], "37.617299")


class TestStockSerializer(TestCase):
    def test_stock_serializer_fields(self):
        store = Store.objects.create(name="Склад", slug="warehouse", address="А", city="Б")
        category = Category.objects.create(title="Кат", slug="cat")
        product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100"),
            category=category,
        )
        stock = Stock.objects.create(product=product, store=store, quantity=10, reserved_quantity=2)
        data = StockSerializer(stock).data
        self.assertEqual(str(data["product"]), str(product.id))
        self.assertEqual(str(data["store"]), str(store.id))
        self.assertEqual(data["quantity"], 10)
        self.assertEqual(data["available_quantity"], 8)


class TestStockReserveForDelivery(TestCase):
    def setUp(self):
        self.store_a = Store.objects.create(name="A", slug="sa", address="1", city="М")
        self.store_b = Store.objects.create(name="B", slug="sb", address="2", city="М")
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="p",
            price=Decimal("10"),
            category=self.category,
        )
        # По 2 в каждом: заказ 4 всегда требует оба склада (порядок store_id не важен).
        Stock.objects.create(product=self.product, store=self.store_a, quantity=2)
        Stock.objects.create(product=self.product, store=self.store_b, quantity=2)

    def test_reserve_splits_across_stores(self):
        with transaction.atomic():
            ok = Stock.reserve_for_delivery(self.product.id, 4)
        self.assertTrue(ok)
        a = Stock.objects.get(product=self.product, store=self.store_a)
        b = Stock.objects.get(product=self.product, store=self.store_b)
        self.assertEqual(a.reserved_quantity, 2)
        self.assertEqual(b.reserved_quantity, 2)

    def test_reserve_fails_when_not_enough_total(self):
        with transaction.atomic():
            ok = Stock.reserve_for_delivery(self.product.id, 10)
        self.assertFalse(ok)
        a = Stock.objects.get(product=self.product, store=self.store_a)
        b = Stock.objects.get(product=self.product, store=self.store_b)
        self.assertEqual(a.reserved_quantity, 0)
        self.assertEqual(b.reserved_quantity, 0)


# --- API (1.3.4) ---


class TestStoreListView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store_active = Store.objects.create(
            name="Активный",
            slug="active-store",
            address="А",
            city="Москва",
            is_active=True,
        )
        self.store_inactive = Store.objects.create(
            name="Неактивный",
            slug="inactive-store",
            address="Б",
            city="Москва",
            is_active=False,
        )

    def test_list_returns_only_active_by_default(self):
        url = reverse("api_v1:stores:store-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        slugs = [s["slug"] for s in data["results"]]
        self.assertIn("active-store", slugs)
        self.assertNotIn("inactive-store", slugs)

    def test_list_filter_by_city(self):
        Store.objects.create(name="В Питере", slug="spb", address="В", city="СПб", is_active=True)
        url = reverse("api_v1:stores:store-list")
        response = self.client.get(url, {"city": "СПб"})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], "spb")

    def test_list_includes_coordinates(self):
        self.store_active.latitude = Decimal("55.75")
        self.store_active.longitude = Decimal("37.61")
        self.store_active.save()
        url = reverse("api_v1:stores:store-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertIsNotNone(results[0].get("coordinates"))


class TestStoreDetailView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store = Store.objects.create(
            name="Детальный",
            slug="detail-store",
            address="Ул. 1",
            city="Город",
            is_active=True,
        )

    def test_retrieve_store(self):
        url = reverse("api_v1:stores:store-detail", kwargs={"pk": self.store.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], "detail-store")
        self.assertIn("coordinates", data)


class TestStockListView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store = Store.objects.create(name="Склад", slug="wh", address="А", city="Б", is_active=True)
        category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="prod",
            price=Decimal("50"),
            category=category,
        )
        Stock.objects.create(product=self.product, store=self.store, quantity=5)

    def test_list_stock_in_store(self):
        url = reverse("api_v1:stores:store-stock", kwargs={"pk": self.store.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["quantity"], 5)


class TestProductStockView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store1 = Store.objects.create(name="М1", slug="m1", address="А", city="Москва", is_active=True)
        self.store2 = Store.objects.create(name="М2", slug="m2", address="Б", city="Москва", is_active=True)
        category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="prod",
            price=Decimal("100"),
            category=category,
        )
        Stock.objects.create(product=self.product, store=self.store1, quantity=3)
        Stock.objects.create(product=self.product, store=self.store2, quantity=7)

    def test_list_product_stock_in_all_stores(self):
        url = reverse("api_v1:products:product-stock", kwargs={"pk": self.product.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)
        quantities = {r["store"]: r["quantity"] for r in data["results"]}
        self.assertEqual(quantities[str(self.store1.id)], 3)
        self.assertEqual(quantities[str(self.store2.id)], 7)
