"""
Unit-тесты приложения cart (задачи 1.4.3, 1.4.4, 1.4.5).
"""

from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Store, Stock
from apps.users.models import CustomUser

from .models import Cart, CartItem
from .services import merge_guest_cart_into_user
from .serializers import (
    CartItemCreateSerializer,
    CartItemSerializer,
    CartSerializer,
    CartItemUpdateSerializer,
)


class TestCartItemSerializer(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=self.category,
        )
        self.store = Store.objects.create(
            name="Магазин",
            slug="store",
            address="А",
            city="Москва",
        )
        self.cart = Cart.objects.create(session_key="test-session")
        self.item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            price_at_add=Decimal("100.00"),
            store=self.store,
        )

    def test_item_serializer_includes_product_store_item_total(self):
        data = CartItemSerializer(self.item).data
        self.assertIn("product", data)
        self.assertEqual(data["product"]["title"], "Товар")
        self.assertIn("store", data)
        self.assertEqual(data["store"]["slug"], "store")
        self.assertEqual(data["quantity"], 2)
        self.assertEqual(data["price_at_add"], "100.00")
        self.assertIn("item_total", data)
        self.assertEqual(Decimal(str(data["item_total"])), Decimal("200.00"))

    def test_item_serializer_store_nullable(self):
        item_no_store = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            price_at_add=Decimal("50.00"),
            store=None,
        )
        data = CartItemSerializer(item_no_store).data
        self.assertIsNone(data["store"])


class TestCartSerializer(TestCase):
    def setUp(self):
        self.cart = Cart.objects.create(session_key="session-1")
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="prod",
            price=Decimal("80.00"),
            category=self.category,
        )
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=3,
            price_at_add=Decimal("80.00"),
        )

    def test_cart_serializer_includes_items_and_total_amount(self):
        data = CartSerializer(self.cart).data
        self.assertIn("items", data)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 3)
        self.assertIn("total_amount", data)
        self.assertEqual(Decimal(str(data["total_amount"])), Decimal("240.00"))


class TestCartItemCreateSerializer(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="М",
            slug="m",
            address="А",
            city="Б",
            is_active=True,
        )

    def test_create_serializer_valid(self):
        data = {
            "product": str(self.product.id),
            "quantity": 2,
            "store": str(self.store.id),
        }
        s = CartItemCreateSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_create_serializer_product_required(self):
        s = CartItemCreateSerializer(data={"quantity": 1})
        self.assertFalse(s.is_valid())
        self.assertIn("product", s.errors)

    def test_create_serializer_invalid_product(self):
        import uuid

        s = CartItemCreateSerializer(data={"product": str(uuid.uuid4()), "quantity": 1})
        self.assertFalse(s.is_valid())
        self.assertIn("product", s.errors)

    def test_create_serializer_quantity_min(self):
        s = CartItemCreateSerializer(
            data={"product": str(self.product.id), "quantity": 0}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("quantity", s.errors)


class TestCartItemUpdateSerializer(TestCase):
    def setUp(self):
        self.cart = Cart.objects.create(session_key="s")
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="p",
            price=Decimal("10.00"),
            category=self.category,
        )
        self.item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            price_at_add=Decimal("10.00"),
        )

    def test_update_serializer_quantity(self):
        data = {"quantity": 5}
        s = CartItemUpdateSerializer(self.item, data=data, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        updated = s.save()
        self.assertEqual(updated.quantity, 5)


# --- API (1.4.4) ---


class TestCartViewAPI(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_get_creates_cart_and_returns_empty(self):
        url = reverse("api_v1:cart:cart")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["items"], [])
        self.assertIn("total_amount", data)


class TestCartItemCreateViewAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="М",
            slug="m",
            address="А",
            city="Б",
            is_active=True,
        )
        Stock.objects.create(product=self.product, store=self.store, quantity=10)

    def test_post_adds_item_returns_cart(self):
        url = reverse("api_v1:cart:cart-item-create")
        response = self.client.post(
            url,
            {"product": str(self.product.id), "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 2)
        self.assertEqual(Decimal(str(data["total_amount"])), Decimal("200.00"))

    def test_post_with_store_checks_stock(self):
        url = reverse("api_v1:cart:cart-item-create")
        response = self.client.post(
            url,
            {
                "product": str(self.product.id),
                "quantity": 5,
                "store": str(self.store.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        Stock.objects.filter(product=self.product, store=self.store).update(
            quantity=2, reserved_quantity=0
        )
        response2 = self.client.post(
            url,
            {
                "product": str(self.product.id),
                "quantity": 3,
                "store": str(self.store.id),
            },
            format="json",
        )
        self.assertEqual(response2.status_code, 400)
        self.assertIn("detail", response2.json())


class TestCartItemDetailViewAPI(TestCase):
    """PATCH/DELETE используют корзину текущей сессии (создаём её через GET + POST)."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("50.00"),
            category=self.category,
            is_active=True,
        )
        self._ensure_cart_with_item()

    def _ensure_cart_with_item(self):
        self.client.get(reverse("api_v1:cart:cart"))
        resp = self.client.post(
            reverse("api_v1:cart:cart-item-create"),
            {"product": str(self.product.id), "quantity": 2},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.item_id = resp.json()["items"][0]["id"]

    def test_patch_updates_quantity(self):
        url = reverse(
            "api_v1:cart:cart-item-detail",
            kwargs={"pk": self.item_id},
        )
        response = self.client.patch(url, {"quantity": 4}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 4)

    def test_patch_quantity_zero_removes_item(self):
        url = reverse(
            "api_v1:cart:cart-item-detail",
            kwargs={"pk": self.item_id},
        )
        response = self.client.patch(url, {"quantity": 0}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 0)

    def test_delete_removes_item(self):
        url = reverse(
            "api_v1:cart:cart-item-detail",
            kwargs={"pk": self.item_id},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(CartItem.objects.filter(pk=self.item_id).exists())

    def test_delete_404_unknown_item(self):
        import uuid

        url = reverse(
            "api_v1:cart:cart-item-detail",
            kwargs={"pk": uuid.uuid4()},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)


class TestCartClearViewAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("10.00"),
            category=self.category,
            is_active=True,
        )
        self.client.get(reverse("api_v1:cart:cart"))
        self.client.post(
            reverse("api_v1:cart:cart-item-create"),
            {"product": str(self.product.id), "quantity": 1},
            format="json",
        )

    def test_post_clears_all_items(self):
        response = self.client.post(reverse("api_v1:cart:cart-clear"))
        self.assertEqual(response.status_code, 204)
        get_resp = self.client.get(reverse("api_v1:cart:cart"))
        self.assertEqual(len(get_resp.json()["items"]), 0)


# --- Связывание корзины при авторизации (1.4.5) ---


class TestMergeGuestCartIntoUser(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.category = Category.objects.create(title="Кат", slug="cat")
        self.product = Product.objects.create(
            title="Товар",
            slug="product",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )
        self.user = CustomUser.objects.create_user(phone="+79991234567", username="+79991234567")

    def _request_with_session(self, session_key):
        request = self.factory.get("/")
        request.session = type("Session", (), {"session_key": session_key})()
        return request

    def test_merge_creates_user_cart_and_moves_items(self):
        session_key = "guest-session-123"
        guest_cart = Cart.objects.create(session_key=session_key, user=None)
        CartItem.objects.create(
            cart=guest_cart,
            product=self.product,
            quantity=2,
            price_at_add=Decimal("100.00"),
        )
        request = self._request_with_session(session_key)
        merge_guest_cart_into_user(request, self.user)

        self.assertFalse(Cart.objects.filter(pk=guest_cart.pk).exists())
        user_cart = Cart.objects.filter(user=self.user).first()
        self.assertIsNotNone(user_cart)
        self.assertEqual(user_cart.items.count(), 1)
        self.assertEqual(user_cart.items.get().quantity, 2)

    def test_merge_combines_same_product_quantity(self):
        session_key = "guest-session-456"
        guest_cart = Cart.objects.create(session_key=session_key, user=None)
        CartItem.objects.create(
            cart=guest_cart,
            product=self.product,
            quantity=1,
            price_at_add=Decimal("100.00"),
        )
        user_cart = Cart.objects.create(user=self.user, session_key=None)
        CartItem.objects.create(
            cart=user_cart,
            product=self.product,
            quantity=3,
            price_at_add=Decimal("100.00"),
            store=None,
        )
        request = self._request_with_session(session_key)
        merge_guest_cart_into_user(request, self.user)

        self.assertFalse(Cart.objects.filter(pk=guest_cart.pk).exists())
        user_cart.refresh_from_db()
        self.assertEqual(user_cart.items.count(), 1)
        self.assertEqual(user_cart.items.get().quantity, 4)

    def test_merge_no_op_when_no_session_key(self):
        request = self.factory.get("/")
        request.session = type("Session", (), {"session_key": None})()
        merge_guest_cart_into_user(request, self.user)
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 0)
