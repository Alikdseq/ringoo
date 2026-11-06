"""SEC-006: guest access token — изоляция гостевых заказов (без legacy phone+number)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders.guest_access import (
    _recovery_cache_key,
    hash_guest_token,
    issue_guest_access_token,
)
from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import CustomUser


def _catalog():
    cat = Category.objects.create(title="C", slug=f"g6-{Category.objects.count()}")
    product = Product.objects.create(
        title="P",
        slug=f"g6p-{Product.objects.count()}",
        price=Decimal("200.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S",
        slug=f"g6s-{Store.objects.count()}",
        address="a",
        city="Москва",
        is_active=True,
    )
    Stock.objects.create(product=product, store=store, quantity=20, reserved_quantity=0)
    return product, store


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec006",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec006s",
        },
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://shop.test",
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
    SBER_ECOM_ENABLED=False,
    YOOKASSA_ENABLED=False,
    ORDER_GUEST_ACCESS_TOKEN_TTL_DAYS=90,
    ORDER_GUEST_RECOVERY_TTL_SECONDS=900,
)
class Sec006GuestAccessTokenTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.product, self.store = _catalog()
        cache.clear()
        mail.outbox.clear()

    def _create_guest_order(self, *, phone="79006110001", name="Guest", email=None):
        body = {
            "full_name": name,
            "phone": phone,
            "delivery_type": "pickup",
            "store": str(self.store.id),
            "payment_type": "cash",
            "items": [
                {
                    "product_id": str(self.product.id),
                    "quantity": 1,
                    "price": "200.00",
                }
            ],
            "total_amount": "200.00",
            "delivery_cost": "0",
            "bonus_used": "0",
            "consent_personal_data": True,
        }
        if email:
            body["email"] = email
        resp = self.api.post("/api/v1/orders/", body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()

    def _legacy_guest_order(self, *, phone="79006118888", email="legacy@example.com"):
        order = Order.objects.create(
            user=None,
            full_name="Legacy",
            phone=phone,
            email=email,
            delivery_type=Order.DELIVERY_PICKUP,
            store=self.store,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("200.00"),
            status=Order.STATUS_NEW,
            consent_personal_data=True,
            guest_access_token_hash="",
            guest_access_token_expires_at=None,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_title=self.product.title,
            quantity=1,
            price=self.product.price,
        )
        return order

    def test_guest_create_returns_token_and_stores_hash_only(self):
        data = self._create_guest_order()
        token = data.get("guest_access_token")
        self.assertTrue(token)
        order = Order.objects.get(pk=data["id"])
        self.assertTrue(order.guest_access_token_hash)
        self.assertEqual(order.guest_access_token_hash, hash_guest_token(token))
        self.assertNotEqual(order.guest_access_token_hash, token)

    def test_guest_with_token_gets_full_track(self):
        data = self._create_guest_order()
        token = data["guest_access_token"]
        resp = self.api.get(
            "/api/v1/orders/track/",
            {
                "order_number": data["order_number"],
                "phone": data["phone"],
                "guest_token": token,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["full_name"], "Guest")
        self.assertIn("phone", resp.json())

    def test_guest_without_token_no_pii_on_track(self):
        data = self._create_guest_order()
        resp = self.api.get(
            "/api/v1/orders/track/",
            {"order_number": data["order_number"], "phone": data["phone"]},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("guest_token_required"))
        self.assertNotIn("full_name", body)
        self.assertNotIn("phone", body)
        self.assertNotIn("email", body)
        self.assertNotIn("delivery_address", body)
        self.assertNotIn("items", body)

    def test_legacy_order_without_hash_denied_pii_by_phone(self):
        """Тест №2: старый гостевой заказ без токена недоступен по номеру и телефону."""
        order = self._legacy_guest_order()
        resp = self.api.get(
            "/api/v1/orders/track/",
            {"order_number": order.order_number, "phone": order.phone},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("guest_token_required"))
        self.assertNotIn("full_name", body)
        self.assertNotIn("phone", body)
        self.assertNotIn("email", body)
        self.assertNotIn("items", body)

        cancel = self.api.post(
            f"/api/v1/orders/{order.pk}/cancel/",
            {"order_number": order.order_number, "phone": order.phone},
            format="json",
        )
        self.assertEqual(cancel.status_code, 403)

    def test_legacy_recover_via_email_then_access(self):
        order = self._legacy_guest_order(email="legacy@example.com")
        r1 = self.api.post(
            "/api/v1/orders/guest-access/recover/",
            {"order_number": order.order_number, "email": "legacy@example.com"},
            format="json",
        )
        r2 = self.api.post(
            "/api/v1/orders/guest-access/recover/",
            {"order_number": "NO-SUCH", "email": "nobody@example.com"},
            format="json",
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json()["detail"], r2.json()["detail"])
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("order-status", body)
        # extract token from link
        token = body.split("token=")[-1].strip().split()[0]
        confirm = self.api.post(
            "/api/v1/orders/guest-access/recover/confirm/",
            {"order_number": order.order_number, "token": token},
            format="json",
        )
        self.assertEqual(confirm.status_code, 200, confirm.content)
        guest_token = confirm.json()["guest_access_token"]
        track = self.api.get(
            "/api/v1/orders/track/",
            {
                "order_number": order.order_number,
                "phone": order.phone,
                "guest_token": guest_token,
            },
        )
        self.assertEqual(track.status_code, 200)
        self.assertEqual(track.json()["full_name"], "Legacy")

    def test_recover_wrong_token_denied(self):
        order = self._legacy_guest_order()
        self.api.post(
            "/api/v1/orders/guest-access/recover/",
            {"order_number": order.order_number, "email": order.email},
            format="json",
        )
        bad = self.api.post(
            "/api/v1/orders/guest-access/recover/confirm/",
            {"order_number": order.order_number, "token": "wrong-token"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)

    def test_recover_expired_token_denied(self):
        order = self._legacy_guest_order()
        self.api.post(
            "/api/v1/orders/guest-access/recover/",
            {"order_number": order.order_number, "email": order.email},
            format="json",
        )
        token = mail.outbox[0].body.split("token=")[-1].strip().split()[0]
        cache.delete(_recovery_cache_key(order.pk))
        expired = self.api.post(
            "/api/v1/orders/guest-access/recover/confirm/",
            {"order_number": order.order_number, "token": token},
            format="json",
        )
        self.assertEqual(expired.status_code, 400)

    def test_recover_token_single_use(self):
        order = self._legacy_guest_order()
        self.api.post(
            "/api/v1/orders/guest-access/recover/",
            {"order_number": order.order_number, "email": order.email},
            format="json",
        )
        token = mail.outbox[0].body.split("token=")[-1].strip().split()[0]
        first = self.api.post(
            "/api/v1/orders/guest-access/recover/confirm/",
            {"order_number": order.order_number, "token": token},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.api.post(
            "/api/v1/orders/guest-access/recover/confirm/",
            {"order_number": order.order_number, "token": token},
            format="json",
        )
        self.assertEqual(second.status_code, 400)

    def test_wrong_token_denied_cancel(self):
        data = self._create_guest_order()
        resp = self.api.post(
            f"/api/v1/orders/{data['id']}/cancel/",
            {
                "order_number": data["order_number"],
                "phone": data["phone"],
                "guest_token": "wrong-token-value",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        order = Order.objects.get(pk=data["id"])
        self.assertEqual(order.status, Order.STATUS_NEW)

    def test_token_of_order_a_does_not_open_order_b(self):
        a = self._create_guest_order(phone="79006110011", name="A")
        b = self._create_guest_order(phone="79006110012", name="B")
        resp = self.api.get(
            "/api/v1/orders/track/",
            {
                "order_number": b["order_number"],
                "phone": b["phone"],
                "guest_token": a["guest_access_token"],
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("guest_token_required"))
        self.assertNotIn("full_name", resp.json())

    def test_phone_and_number_without_token_cannot_cancel(self):
        data = self._create_guest_order()
        resp = self.api.post(
            f"/api/v1/orders/{data['id']}/cancel/",
            {"order_number": data["order_number"], "phone": data["phone"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_phone_and_number_without_token_cannot_pay(self):
        data = self._create_guest_order()
        order = Order.objects.get(pk=data["id"])
        order.payment_type = Order.PAYMENT_ONLINE
        order.save(update_fields=["payment_type"])
        resp = self.api.post(
            f"/api/v1/orders/{data['id']}/pay/",
            {"order_number": data["order_number"], "phone": data["phone"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_valid_token_can_cancel(self):
        data = self._create_guest_order()
        resp = self.api.post(
            f"/api/v1/orders/{data['id']}/cancel/",
            {
                "order_number": data["order_number"],
                "phone": data["phone"],
                "guest_token": data["guest_access_token"],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        order = Order.objects.get(pk=data["id"])
        self.assertEqual(order.status, Order.STATUS_CANCELLED)

    def test_expired_token_rejected(self):
        data = self._create_guest_order()
        order = Order.objects.get(pk=data["id"])
        order.guest_access_token_expires_at = timezone.now() - timedelta(hours=1)
        order.save(update_fields=["guest_access_token_expires_at"])
        resp = self.api.post(
            f"/api/v1/orders/{data['id']}/cancel/",
            {
                "guest_token": data["guest_access_token"],
                "order_number": data["order_number"],
                "phone": data["phone"],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_owner_still_accesses_own_order(self):
        user = CustomUser.objects.create_user(phone="79006119999", password="pass12345")
        self.api.force_authenticate(user=user)
        resp = self.api.post(
            "/api/v1/orders/",
            {
                "full_name": "Owner",
                "phone": user.phone,
                "delivery_type": "pickup",
                "store": str(self.store.id),
                "payment_type": "cash",
                "items": [
                    {
                        "product_id": str(self.product.id),
                        "quantity": 1,
                        "price": "200.00",
                    }
                ],
                "total_amount": "200.00",
                "delivery_cost": "0",
                "bonus_used": "0",
                "consent_personal_data": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertNotIn("guest_access_token", resp.json())
        detail = self.api.get(f"/api/v1/orders/{resp.json()['id']}/")
        self.assertEqual(detail.status_code, 200)

    def test_recover_without_email_on_order_sends_nothing(self):
        order = self._legacy_guest_order(email="")
        order.email = None
        order.save(update_fields=["email"])
        resp = self.api.post(
            "/api/v1/orders/guest-access/recover/",
            {"order_number": order.order_number, "email": "any@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
