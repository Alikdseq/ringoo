"""Корзина при online: не очищается до подтверждённой оплаты."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.cart.checkout_clear import clear_cart_after_successful_payment
from apps.cart.models import Cart, CartItem
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.yookassa_service import (
    initiate_yookassa_payment,
    sync_payment_from_yookassa,
)
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.payments.services import PaymentError


def _catalog():
    cat = Category.objects.create(title="Cat", slug=f"c-{Category.objects.count()}")
    product = Product.objects.create(
        title="Phone",
        slug=f"p-{Product.objects.count()}",
        price=Decimal("1500.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S", slug=f"s-{Store.objects.count()}", address="a", city="c"
    )
    Stock.objects.create(product=product, store=store, quantity=10, reserved_quantity=0)
    return product, store


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    YOOKASSA_API_URL="https://api.yookassa.ru/v3",
    SBER_ECOM_ENABLED=False,
)
class OnlineCartRetentionTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.product, self.store = _catalog()

    def _seed_session_cart(self):
        session = self.api.session
        session.save()
        cart = Cart.objects.create(session_key=session.session_key, user=None)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2,
            price_at_add=self.product.price,
        )
        return cart

    def _order_payload(self, *, payment_type: str):
        return {
            "from_cart": True,
            "full_name": "Иван Тестов",
            "phone": "79001112233",
            "email": "t@example.com",
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": payment_type,
            "items": [
                {
                    "product_id": str(self.product.id),
                    "quantity": 2,
                    "price": "1500.00",
                }
            ],
            "total_amount": "3000.00",
            "delivery_cost": "0",
            "bonus_used": "0",
            "consent_personal_data": True,
        }

    def _create_online_order_with_cart(self):
        cart = self._seed_session_cart()
        resp = self.api.post(
            "/api/v1/orders/", self._order_payload(payment_type="online"), format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        order = Order.objects.get(pk=resp.data["id"])
        return cart, order

    def test_cash_order_clears_cart(self):
        cart = self._seed_session_cart()
        self.assertEqual(cart.items.count(), 1)
        resp = self.api.post(
            "/api/v1/orders/", self._order_payload(payment_type="cash"), format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)

    def test_online_order_keeps_cart_and_stores_cart_id(self):
        cart, order = self._create_online_order_with_cart()
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.get().quantity, 2)
        self.assertEqual(order.checkout_cart_id, cart.id)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_confirmation_url_does_not_clear_cart(self, MockClient):
        cart, order = self._create_online_order_with_cart()
        api = MockClient.return_value
        api.create_payment.return_value = {
            "id": "yk-create-1",
            "status": "pending",
            "amount": {"value": "3000.00", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "confirmation_url": "https://yoomoney.ru/checkout/payments/v2/contract?orderId=1",
            },
            "paid": False,
            "test": True,
            "metadata": {"order_id": str(order.id)},
        }
        result = initiate_yookassa_payment(order, client=api)
        self.assertTrue(result.form_url)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.checkout_cart_id, cart.id)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_pending_payment_does_not_clear_cart(self, MockClient):
        cart, order = self._create_online_order_with_cart()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=300000,
            currency="RUB",
            merchant_order_number="a" * 32,
            yookassa_payment_id="yk-pending",
            form_url="https://pay.example/x",
            is_test=True,
        )
        MockClient.return_value.get_payment.return_value = {
            "id": "yk-pending",
            "status": "pending",
            "amount": {"value": "3000.00", "currency": "RUB"},
            "metadata": {"order_id": str(order.id), "payment_id": str(payment.id)},
            "test": True,
        }
        with self.captureOnCommitCallbacks(execute=True):
            sync_payment_from_yookassa(payment, client=MockClient.return_value)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.checkout_cart_id, cart.id)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_canceled_payment_does_not_clear_cart(self, MockClient):
        cart, order = self._create_online_order_with_cart()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=300000,
            currency="RUB",
            merchant_order_number="b" * 32,
            yookassa_payment_id="yk-cancel",
            form_url="https://pay.example/x",
        )
        MockClient.return_value.get_payment.return_value = {
            "id": "yk-cancel",
            "status": "canceled",
            "amount": {"value": "3000.00", "currency": "RUB"},
            "metadata": {"order_id": str(order.id), "payment_id": str(payment.id)},
            "cancellation_details": {"reason": "canceled_by_merchant"},
        }
        with self.captureOnCommitCallbacks(execute=True):
            sync_payment_from_yookassa(payment, client=MockClient.return_value)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_status_check_error_does_not_clear_cart(self, MockClient):
        from integrations.yookassa.client import YooKassaError

        cart, order = self._create_online_order_with_cart()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=300000,
            currency="RUB",
            merchant_order_number="e" * 32,
            yookassa_payment_id="yk-err",
            form_url="https://pay.example/x",
        )
        MockClient.return_value.get_payment.side_effect = YooKassaError(
            "timeout", code="yookassa_http_error"
        )
        with self.assertRaises(PaymentError):
            sync_payment_from_yookassa(payment, client=MockClient.return_value)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.checkout_cart_id, cart.id)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_succeeded_clears_cart_idempotently(self, MockClient):
        cart, order = self._create_online_order_with_cart()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=300000,
            currency="RUB",
            merchant_order_number="c" * 32,
            yookassa_payment_id="yk-ok",
            form_url="https://pay.example/x",
        )
        MockClient.return_value.get_payment.return_value = {
            "id": "yk-ok",
            "status": "succeeded",
            "amount": {"value": "3000.00", "currency": "RUB"},
            "metadata": {"order_id": str(order.id), "payment_id": str(payment.id)},
            "test": True,
        }
        with self.captureOnCommitCallbacks(execute=True):
            updated = sync_payment_from_yookassa(payment, client=MockClient.return_value)
        self.assertEqual(updated.status, Payment.STATUS_PAID)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)
        order.refresh_from_db()
        self.assertIsNone(order.checkout_cart_id)

        # Повторная очистка / sync не падает и не дублирует эффекты
        again = clear_cart_after_successful_payment(order)
        self.assertTrue(again["already_cleared"])
        with self.captureOnCommitCallbacks(execute=True):
            updated2 = sync_payment_from_yookassa(payment, client=MockClient.return_value)
        self.assertEqual(updated2.status, Payment.STATUS_PAID)
        self.assertEqual(cart.items.count(), 0)

    def test_clear_helper_without_cart_id_is_noop(self):
        order = Order.objects.create(
            full_name="X",
            phone="79001112233",
            delivery_type=Order.DELIVERY_PICKUP,
            store=self.store,
            payment_type=Order.PAYMENT_ONLINE,
            status=Order.STATUS_NEW,
            total_amount=Decimal("10.00"),
            consent_personal_data=True,
            checkout_cart_id=None,
        )
        report = clear_cart_after_successful_payment(order)
        self.assertTrue(report["already_cleared"])
        self.assertEqual(report["qty_removed"], 0)

    def test_unpaid_cart_survives_reload_via_session(self):
        """После «перезагрузки» (новый запрос с той же session) корзина на месте."""
        cart, _order = self._create_online_order_with_cart()
        # Имитация reload: запрос корзины тем же клиентом/сессией
        resp = self.api.get("/api/v1/cart/")
        self.assertEqual(resp.status_code, 200, resp.content)
        items = resp.data.get("items") or []
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["quantity"], 2)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)

    def _pay_succeeded(self, order, payment_id="yk-pay-x", MockClient=None):
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=int(order.total_amount * 100),
            currency="RUB",
            merchant_order_number=payment_id.replace("-", "")[:32].ljust(32, "0"),
            yookassa_payment_id=payment_id,
            form_url="https://pay.example/x",
        )
        client = MockClient.return_value if MockClient else None
        if client is None:
            raise AssertionError("MockClient required")
        client.get_payment.return_value = {
            "id": payment_id,
            "status": "succeeded",
            "amount": {"value": f"{order.total_amount:.2f}", "currency": "RUB"},
            "metadata": {"order_id": str(order.id), "payment_id": str(payment.id)},
            "test": True,
        }
        with self.captureOnCommitCallbacks(execute=True):
            return sync_payment_from_yookassa(payment, client=client)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_pay_old_order_keeps_new_cart_item(self, MockClient):
        """Оплата старого заказа не удаляет товар, добавленный после оформления."""
        product_b = Product.objects.create(
            title="Phone B",
            slug="p-b-extra",
            price=Decimal("500.00"),
            category=self.product.category,
            is_active=True,
        )
        Stock.objects.create(
            product=product_b, store=self.store, quantity=10, reserved_quantity=0
        )
        cart, order = self._create_online_order_with_cart()
        # После заказа добавили новый товар
        CartItem.objects.create(
            cart=cart,
            product=product_b,
            quantity=1,
            price_at_add=product_b.price,
        )
        self.assertEqual(cart.items.count(), 2)

        updated = self._pay_succeeded(order, payment_id="yk-keep-new", MockClient=MockClient)
        self.assertEqual(updated.status, Payment.STATUS_PAID)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        left = cart.items.get()
        self.assertEqual(left.product_id, product_b.id)
        self.assertEqual(left.quantity, 1)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_pay_old_order_preserves_increased_qty(self, MockClient):
        """Заказали 2, потом увеличили до 5 → после оплаты остаётся 3."""
        cart, order = self._create_online_order_with_cart()
        item = cart.items.get()
        item.quantity = 5
        item.save(update_fields=["quantity", "updated_at"])

        updated = self._pay_succeeded(order, payment_id="yk-qty-up", MockClient=MockClient)
        self.assertEqual(updated.status, Payment.STATUS_PAID)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.get().quantity, 3)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_pay_old_order_after_item_removed(self, MockClient):
        """Товар удалили из корзины до оплаты — clear не падает, других не трогает."""
        product_b = Product.objects.create(
            title="Extra",
            slug="p-extra-rm",
            price=Decimal("200.00"),
            category=self.product.category,
            is_active=True,
        )
        Stock.objects.create(
            product=product_b, store=self.store, quantity=5, reserved_quantity=0
        )
        cart, order = self._create_online_order_with_cart()
        cart.items.all().delete()
        CartItem.objects.create(
            cart=cart,
            product=product_b,
            quantity=4,
            price_at_add=product_b.price,
        )

        updated = self._pay_succeeded(order, payment_id="yk-rm", MockClient=MockClient)
        self.assertEqual(updated.status, Payment.STATUS_PAID)
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.get().product_id, product_b.id)
        self.assertEqual(cart.items.get().quantity, 4)

    @patch("apps.payments.yookassa_service.YooKassaClient")
    def test_two_unpaid_orders_pay_second_only(self, MockClient):
        """Два неоплаченных заказа: оплата второго вычитает только его qty."""
        cart, order1 = self._create_online_order_with_cart()
        # Второй заказ из той же корзины (qty всё ещё 2)
        resp2 = self.api.post(
            "/api/v1/orders/", self._order_payload(payment_type="online"), format="json"
        )
        self.assertEqual(resp2.status_code, 201, resp2.content)
        order2 = Order.objects.get(pk=resp2.data["id"])
        self.assertEqual(order2.checkout_cart_id, cart.id)
        # Корзина всё ещё с 2 шт.
        cart.refresh_from_db()
        self.assertEqual(cart.items.get().quantity, 2)

        updated = self._pay_succeeded(order2, payment_id="yk-ord2", MockClient=MockClient)
        self.assertEqual(updated.status, Payment.STATUS_PAID)
        cart.refresh_from_db()
        # order2 был на 2 шт. → корзина пуста; order1 ещё неоплачен
        self.assertEqual(cart.items.count(), 0)
        order1.refresh_from_db()
        self.assertEqual(order1.checkout_cart_id, cart.id)

    def test_merge_retargets_checkout_cart_id(self):
        from apps.cart.services import merge_guest_cart_into_user
        from apps.users.models import CustomUser
        from rest_framework.test import APIRequestFactory

        cart, order = self._create_online_order_with_cart()
        user = CustomUser.objects.create_user("79005556677", password="pass12345")
        factory = APIRequestFactory()
        request = factory.get("/")
        request.session = type(
            "S", (), {"session_key": self.api.session.session_key}
        )()
        merge_guest_cart_into_user(request, user)
        order.refresh_from_db()
        user_cart = Cart.objects.get(user=user)
        self.assertEqual(order.checkout_cart_id, user_cart.id)
        self.assertFalse(Cart.objects.filter(pk=cart.pk).exists())
        self.assertEqual(user_cart.items.get().quantity, 2)
