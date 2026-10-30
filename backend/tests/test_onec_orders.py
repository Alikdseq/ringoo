"""Мок-тесты SiteOrders, резерва серий, guest reg, URL, stub retries."""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.orders.models import Order, OrderItem
from apps.orders.services import cancel_order_and_release_stock
from apps.orders.tasks import sync_order_to_onec_task
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from apps.users.models import UserProfile
from integrations.onec.client import OneCClient, OneCClientError
from integrations.onec.importer import diagnose_stale_blank_series_stocks
from integrations.onec.orders import (
    OneCOrderSyncBlocked,
    plan_and_reserve_at_store,
    resolve_warehouse_id,
    sync_order_to_onec,
)
from integrations.onec.registration import register_user_in_onec
from integrations.onec.url_utils import OneCBaseUrlError, normalize_onec_base_url

User = get_user_model()

WH_A = "22222222-2222-4222-8222-222222222222"
CLIENT_ID = "44444444-4444-4444-8444-444444444444"
SERIES_A = "33333333-3333-4333-8333-333333333333"
SERIES_B = "55555555-5555-4555-8555-555555555555"
DOC_ORDER = "66666666-6666-4666-8666-666666666666"
DOC_SALE = "77777777-7777-4777-8777-777777777777"


class _FakeHTTPResponse:
    def __init__(self, body: bytes, status: int = 200, content_type: str = "application/json"):
        self._body = body
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self, n: int = -1):
        if n is None or n < 0:
            return self._body
        return self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@override_settings(
    ONE_C_API_ENABLED=True,
    ONE_C_ORDER_SYNC_ENABLED=True,
    ONE_C_API_BASE_URL="http://example.test/razrab/hs",
)
class OneCOrdersSyncTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title="Phones", slug="phones")
        self.store = Store.objects.create(
            name="Магазин А",
            slug="store-a",
            address="ул. Тест",
            city="Город",
            onec_warehouse_id=WH_A,
        )
        self.product = Product.objects.create(
            title="iPhone Test",
            slug="iphone-test",
            sku="SKU-1",
            category=self.category,
            price=Decimal("5500.00"),
            onec_code="00-00034618",
            is_active=True,
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            onec_series_id="",
        )

    def _order(self, *, user=None, **kwargs):
        order = Order.objects.create(
            user=user,
            full_name=kwargs.get("full_name", "Иванов Иван Иванович"),
            phone=kwargs.get("phone", "+79991234567"),
            delivery_type=Order.DELIVERY_PICKUP,
            store=self.store,
            payment_type=Order.PAYMENT_ONLINE,
            total_amount=Decimal("5500.00"),
            status=Order.STATUS_NEW,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_title=self.product.title,
            product_sku=self.product.sku,
            quantity=1,
            price=Decimal("5500.00"),
            item_total=Decimal("5500.00"),
            onec_product_code="00-00034618",
            onec_series_id=kwargs.get("series_id", ""),
        )
        return order

    def _client(self):
        return OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="u",
            password="p",
        )

    def test_endpoints_and_warehouse_from_store(self):
        c = self._client()
        self.assertTrue(c.build_url(c.endpoints.orders).endswith("SiteOrders/orders"))
        self.assertIn("/razrab/hs/", c.base_url)
        order = self._order()
        self.assertEqual(resolve_warehouse_id(order), WH_A)
        delivery = self._order()
        delivery.delivery_type = Order.DELIVERY_DELIVERY
        delivery.save()
        self.assertEqual(resolve_warehouse_id(delivery), WH_A)

    def test_register_parses_client_id(self):
        user = User.objects.create_user(phone="79001110001", password="pass12345")
        UserProfile.objects.create(user=user, first_name="Иван", last_name="Иванов")
        body = json.dumps({"ClientId": CLIENT_ID, "created": True}).encode()
        with patch.object(
            OneCClient,
            "_http_open",
            return_value=_FakeHTTPResponse(body, status=201),
        ):
            result = register_user_in_onec(user, client=self._client())
        user.refresh_from_db()
        self.assertEqual(result.partner_id, CLIENT_ID)

    def test_guest_timeout_marks_pending_review_no_auto_retry(self):
        order = self._order()
        api = MagicMock()
        api.register_partner.side_effect = OneCClientError("timeout", status_code=None)
        result = sync_order_to_onec(order.pk, paid=False, client=api)
        self.assertFalse(result.get("ok"))
        order.refresh_from_db()
        self.assertEqual(order.onec_sync_status, Order.ONEC_SYNC_PENDING_REVIEW)
        api.create_or_update_order.assert_not_called()
        # повтор без force не шлёт регистрацию снова
        api2 = MagicMock()
        again = sync_order_to_onec(order.pk, paid=False, client=api2)
        self.assertTrue(again.get("skipped"))
        api2.register_partner.assert_not_called()

    def test_guest_http_500_no_unsafe_retry(self):
        order = self._order()
        api = MagicMock()
        api.register_partner.side_effect = OneCClientError("500", status_code=500)
        result = sync_order_to_onec(order.pk, paid=False, client=api)
        self.assertFalse(result.get("ok"))
        order.refresh_from_db()
        self.assertEqual(order.onec_sync_status, Order.ONEC_SYNC_PENDING_REVIEW)
        api.create_or_update_order.assert_not_called()

    def test_sync_paid_false_then_true_same_order_id(self):
        order = self._order()
        user = User.objects.create_user(phone="79001110002", password="pass12345")
        user.onec_partner_id = CLIENT_ID
        user.save(update_fields=["onec_partner_id"])
        order.user = user
        order.save(update_fields=["user"])

        captured = []

        def fake_create(payload):
            captured.append(dict(payload))
            if not payload["paid"]:
                return {
                    "orderId": payload["orderId"],
                    "documentType": "ЗаказКлиента",
                    "documentId": DOC_ORDER,
                    "documentNumber": "0000-000123",
                    "created": True,
                    "posted": False,
                    "http_status": 201,
                }
            return {
                "orderId": payload["orderId"],
                "documentType": "РеализацияТоваровУслуг",
                "documentId": DOC_SALE,
                "documentNumber": "0000-000124",
                "created": True,
                "posted": True,
                "http_status": 201,
            }

        api = MagicMock()
        api.create_or_update_order.side_effect = fake_create
        r1 = sync_order_to_onec(order.pk, paid=False, client=api)
        self.assertTrue(r1["ok"])
        r2 = sync_order_to_onec(order.pk, paid=True, client=api)
        self.assertTrue(r2["ok"])
        self.assertEqual(captured[0]["orderId"], captured[1]["orderId"])
        self.assertEqual(captured[0]["items"], captured[1]["items"])
        self.assertEqual(captured[0]["warehouseId"], WH_A)

    def test_missing_document_id_not_synced(self):
        order = self._order()
        user = User.objects.create_user(phone="79001110009", password="x")
        user.onec_partner_id = CLIENT_ID
        user.save()
        order.user = user
        order.save()
        api = MagicMock()
        api.create_or_update_order.return_value = {
            "orderId": str(order.pk),
            "created": True,
            "posted": False,
            "http_status": 201,
        }
        result = sync_order_to_onec(order.pk, paid=False, client=api)
        self.assertFalse(result.get("ok"))
        order.refresh_from_db()
        self.assertEqual(order.onec_sync_status, Order.ONEC_SYNC_PENDING_REVIEW)
        self.assertFalse(order.onec_document_id)

    def test_bad_base_url_blocks_without_network(self):
        order = self._order()
        user = User.objects.create_user(phone="79001110010", password="x")
        user.onec_partner_id = CLIENT_ID
        user.save()
        order.user = user
        order.save()
        api = MagicMock()
        with override_settings(ONE_C_API_BASE_URL="http://example.test/ut11_test/hs"):
            result = sync_order_to_onec(order.pk, paid=False, client=api)
        self.assertTrue(result.get("blocked") or not result.get("ok"))
        api.create_or_update_order.assert_not_called()
        api.register_partner.assert_not_called()

    def test_cancel_releases_store_reservation(self):
        order = self._order()
        Stock.objects.filter(product=self.product, store=self.store).update(
            quantity=5, reserved_quantity=1
        )
        cancel_order_and_release_stock(order, reason="test")
        row = Stock.objects.get(product=self.product, store=self.store, onec_series_id="")
        self.assertEqual(row.reserved_quantity, 0)


class OneCUrlUtilsTests(TestCase):
    def test_normalize_slash_variants(self):
        a = normalize_onec_base_url("http://example.test/razrab/hs")
        b = normalize_onec_base_url("http://example.test/razrab/hs/")
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("/razrab/hs/"))

    def test_reject_ut11_and_double_path(self):
        with self.assertRaises(OneCBaseUrlError):
            normalize_onec_base_url("http://example.test/ut11_test/hs")
        with self.assertRaises(OneCBaseUrlError):
            normalize_onec_base_url("http://example.test/razrab/hs/razrab/hs")


class OneCSeriesReserveTests(TransactionTestCase):
    def setUp(self):
        self.category = Category.objects.create(title="Phones", slug="phones-s")
        self.store = Store.objects.create(
            name="A", slug="store-ser", address="a", city="c", onec_warehouse_id=WH_A
        )
        self.product = Product.objects.create(
            title="Serial",
            slug="serial-phone",
            sku="SER-1",
            category=self.category,
            price=Decimal("1000.00"),
            onec_code="00-00000001",
            is_active=True,
        )
        Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=1,
            onec_series_id=SERIES_A,
        )

    def test_second_reserve_same_series_fails(self):
        lines1 = plan_and_reserve_at_store(
            product=self.product,
            quantity=1,
            price=Decimal("1000.00"),
            store_id=self.store.pk,
        )
        self.assertEqual(lines1[0]["onec_series_id"], SERIES_A)
        from integrations.onec.orders import InsufficientStockAtStore

        with self.assertRaises(InsufficientStockAtStore):
            plan_and_reserve_at_store(
                product=self.product,
                quantity=1,
                price=Decimal("1000.00"),
                store_id=self.store.pk,
            )
        row = Stock.objects.get(onec_series_id=SERIES_A)
        self.assertEqual(row.reserved_quantity, 1)

    def test_does_not_take_series_from_other_store(self):
        other = Store.objects.create(
            name="B", slug="store-ser-b", address="b", city="c", onec_warehouse_id="x"
        )
        Stock.objects.create(
            product=self.product,
            store=other,
            quantity=1,
            onec_series_id=SERIES_B,
        )
        from integrations.onec.orders import InsufficientStockAtStore

        Stock.objects.filter(onec_series_id=SERIES_A).update(quantity=0)
        with self.assertRaises(InsufficientStockAtStore):
            plan_and_reserve_at_store(
                product=self.product,
                quantity=1,
                price=Decimal("1000.00"),
                store_id=self.store.pk,
            )


class OneCStubRetryTests(TestCase):
    def test_stub_does_not_recurse_on_retryable(self):
        from config.optional_task import is_celery_available

        if is_celery_available():
            self.skipTest("Real Celery installed — stub recursion N/A")

        with patch(
            "integrations.onec.orders.sync_order_to_onec",
            side_effect=__import__(
                "integrations.onec.orders", fromlist=["OneCOrderSyncError"]
            ).OneCOrderSyncError("tmp", retryable=True, status_code=500),
        ):
            # Nested delay must not explode: task catches and returns without re-delay in stub
            result = sync_order_to_onec_task.delay("00000000-0000-0000-0000-000000000001")
        self.assertFalse(result.get("ok"))


class OneCStockDiagnoseTests(TestCase):
    def test_diagnose_blank_series_when_serial_exists(self):
        cat = Category.objects.create(title="C", slug="c-diag")
        store = Store.objects.create(name="S", slug="s-diag", address="a", city="c")
        product = Product.objects.create(
            title="P", slug="p-diag", category=cat, price=Decimal("1"), is_active=True
        )
        Stock.objects.create(
            product=product, store=store, quantity=2, onec_series_id=""
        )
        Stock.objects.create(
            product=product, store=store, quantity=1, onec_series_id=SERIES_A
        )
        report = diagnose_stale_blank_series_stocks()
        self.assertGreaterEqual(report["suspect_count"], 1)
        self.assertEqual(report["action"], "report_only")
