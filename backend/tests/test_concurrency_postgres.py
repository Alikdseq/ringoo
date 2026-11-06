"""
Конкурентные сценарии — только PostgreSQL (не SQLite).

Запуск на изолированной тестовой БД (НЕ production):

  set RINGOO_TEST_POSTGRES=1
  set DATABASE_URL=postgres://USER:PASS@127.0.0.1:5432/ringoo_test
  set DJANGO_SETTINGS_MODULE=config.settings.test_postgres
  pytest tests/test_concurrency_postgres.py -q --no-cov

Без RINGOO_TEST_POSTGRES модуль skip — конкурентность на SQLite не считается доказанной.
"""

from __future__ import annotations

import os
import threading
import unittest
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.db import connection, connections
from django.test import TransactionTestCase, override_settings

from apps.orders.models import Order, OrderItem
from apps.orders.services import cancel_order_and_release_stock
from apps.payments.models import Payment
from apps.payments.services import handle_sber_callback, sync_payment_from_bank
from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from integrations.onec.orders import InsufficientStockAtStore, plan_and_reserve_at_store

pytestmark = pytest.mark.skipif(
    os.getenv("RINGOO_TEST_POSTGRES", "").strip().lower() not in ("1", "true", "yes"),
    reason="Set RINGOO_TEST_POSTGRES=1 + config.settings.test_postgres",
)


def _require_postgres():
    # unittest.SkipTest — корректно для manage.py test; pytest.skip даёт ERROR в Django runner.
    if os.getenv("RINGOO_TEST_POSTGRES", "").strip().lower() not in ("1", "true", "yes"):
        raise unittest.SkipTest("Set RINGOO_TEST_POSTGRES=1 + config.settings.test_postgres")
    if connection.vendor != "postgresql":
        raise unittest.SkipTest("Requires PostgreSQL, got %s" % connection.vendor)


def _base_order(*, qty: int = 1, reserved: int = 0, series_id: str = ""):
    n = Category.objects.count()
    cat = Category.objects.create(title="C", slug=f"pgc-{n}")
    product = Product.objects.create(
        title="P",
        slug=f"pgp-{n}",
        price=Decimal("1000.00"),
        category=cat,
        is_active=True,
    )
    store = Store.objects.create(
        name="S",
        slug=f"pgs-{n}",
        address="a",
        city="c",
        onec_warehouse_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    )
    Stock.objects.create(
        product=product,
        store=store,
        quantity=qty,
        reserved_quantity=reserved,
        onec_series_id=series_id or "",
        onec_series_name="ser" if series_id else "",
    )
    order = Order.objects.create(
        full_name="T",
        phone="79001112233",
        delivery_type=Order.DELIVERY_PICKUP,
        store=store,
        payment_type=Order.PAYMENT_ONLINE,
        status=Order.STATUS_NEW,
        total_amount=Decimal("1000.00"),
        delivery_cost=Decimal("0"),
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=1,
        price=Decimal("1000.00"),
        item_total=Decimal("1000.00"),
        onec_series_id=series_id or "",
    )
    return order, product, store


def _paid_bank_payload(payment: Payment) -> dict:
    return {
        "errorCode": "0",
        "orderStatus": 2,
        "actionCode": 0,
        "amount": 100000,
        "orderNumber": payment.merchant_order_number,
        "currency": "643",
    }


@override_settings(
    SBER_ECOM_ENABLED=True,
    SBER_ECOM_CALLBACK_TOKEN_REQUIRED=False,
    LATE_ONLINE_PAYMENT_POLICY="manual",
)
class PostgresPaymentConcurrencyTests(TransactionTestCase):
    def setUp(self):
        _require_postgres()

    def test_two_parallel_sync_yield_single_paid(self):
        order, _, _ = _base_order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="pg-par-1",
            sber_order_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            form_url="https://ecomtest.sberbank.ru/pp/x",
            currency="643",
        )
        mock = MagicMock()
        mock.get_order_status.return_value = _paid_bank_payload(payment)
        errors: list[BaseException] = []

        def worker():
            try:
                connections.close_all()
                sync_payment_from_bank(Payment.objects.get(pk=payment.pk), client=mock)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(
            Payment.objects.filter(order=order, status=Payment.STATUS_PAID).count(), 1
        )

    def test_two_parallel_callbacks_idempotent(self):
        order, _, _ = _base_order()
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="pg-cb-1",
            sber_order_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            form_url="https://ecomtest.sberbank.ru/pp/x",
            currency="643",
        )
        mock = MagicMock()
        mock.get_order_status.return_value = _paid_bank_payload(payment)
        payload = {
            "mdOrder": payment.sber_order_id,
            "orderNumber": payment.merchant_order_number,
            "operation": "deposited",
            "status": 1,
        }

        def worker():
            connections.close_all()
            handle_sber_callback(payload, client=mock)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(
            Payment.objects.filter(order=order, status=Payment.STATUS_PAID).count(), 1
        )

    def test_cancel_concurrent_with_bank_paid(self):
        order, _, _ = _base_order(qty=1, reserved=1)
        payment = Payment.objects.create(
            order=order,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="pg-cancel-pay",
            sber_order_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            form_url="https://ecomtest.sberbank.ru/pp/x",
            currency="643",
        )
        mock = MagicMock()
        mock.get_order_status.return_value = _paid_bank_payload(payment)
        oid, pid = order.pk, payment.pk

        def do_cancel():
            connections.close_all()
            cancel_order_and_release_stock(Order.objects.get(pk=oid), reason="race")

        def do_pay():
            connections.close_all()
            sync_payment_from_bank(Payment.objects.get(pk=pid), client=mock)

        t1 = threading.Thread(target=do_cancel)
        t2 = threading.Thread(target=do_pay)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        order.refresh_from_db()
        payment.refresh_from_db()
        paid_n = Payment.objects.filter(order_id=oid, status=Payment.STATUS_PAID).count()
        self.assertLessEqual(paid_n, 1)
        # Честные исходы: cancelled + needs_review|failed|pending, либо confirmed + paid
        if order.status == Order.STATUS_CANCELLED:
            self.assertNotEqual(
                (payment.status == Payment.STATUS_PAID and paid_n == 1),
                True,
                msg="cancelled order must not stay silently paid under manual late policy",
            )
            self.assertIn(
                payment.status,
                {
                    Payment.STATUS_NEEDS_REVIEW,
                    Payment.STATUS_FAILED,
                    Payment.STATUS_PENDING,
                    Payment.STATUS_REGISTERED,
                    Payment.STATUS_REVERSED,
                },
            )
        elif payment.status == Payment.STATUS_PAID:
            self.assertEqual(order.status, Order.STATUS_CONFIRMED)


@override_settings(
    YOOKASSA_ENABLED=True,
    YOOKASSA_TEST_MODE=True,
    YOOKASSA_SHOP_ID="shop-test",
    YOOKASSA_SECRET_KEY="test_secret_key_value",
    SBER_ECOM_ENABLED=False,
    LATE_ONLINE_PAYMENT_POLICY="manual",
)
class PostgresYooKassaConcurrencyTests(TransactionTestCase):
    """Оплата ЮKassa vs expire / параллельный sync (INT closeout)."""

    def setUp(self):
        _require_postgres()

    def test_two_parallel_yk_sync_single_paid(self):
        from apps.payments.yookassa_service import sync_payment_from_yookassa

        order, _, _ = _base_order()
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="pg-yk-1",
            yookassa_payment_id="yk-pg-parallel",
            form_url="https://yoomoney.ru/x",
            currency="RUB",
        )
        payload = {
            "id": "yk-pg-parallel",
            "status": "succeeded",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "metadata": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
            "test": True,
        }
        mock = MagicMock()
        mock.get_payment.return_value = payload
        errors: list[BaseException] = []

        def worker():
            try:
                connections.close_all()
                sync_payment_from_yookassa(
                    Payment.objects.get(pk=payment.pk), client=mock
                )
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(
            Payment.objects.filter(order=order, status=Payment.STATUS_PAID).count(), 1
        )

    def test_expire_concurrent_with_yk_paid(self):
        from django.utils import timezone
        from datetime import timedelta

        from apps.payments.services import expire_unpaid_online_orders
        from apps.payments.yookassa_service import sync_payment_from_yookassa

        order, product, store = _base_order(qty=1, reserved=1)
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=60)
        )
        payment = Payment.objects.create(
            order=order,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_PENDING,
            amount=order.total_amount,
            amount_kopecks=100000,
            merchant_order_number="pg-yk-exp",
            yookassa_payment_id="yk-pg-expire",
            form_url="https://yoomoney.ru/x",
            currency="RUB",
        )
        payload = {
            "id": "yk-pg-expire",
            "status": "succeeded",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "metadata": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
            "test": True,
        }
        mock = MagicMock()
        mock.get_payment.return_value = payload
        oid, pid = order.pk, payment.pk

        def do_expire():
            connections.close_all()
            with override_settings(
                YOOKASSA_ENABLED=True,
                SBER_ECOM_ENABLED=False,
            ):
                # sync inside expire uses real YooKassaClient — patch via module
                from unittest.mock import patch

                with patch(
                    "apps.payments.yookassa_service.YooKassaClient",
                    return_value=mock,
                ):
                    expire_unpaid_online_orders()

        def do_pay():
            connections.close_all()
            sync_payment_from_yookassa(
                Payment.objects.get(pk=pid), client=mock
            )

        t1 = threading.Thread(target=do_expire)
        t2 = threading.Thread(target=do_pay)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        order.refresh_from_db()
        payment.refresh_from_db()
        stock = Stock.objects.get(product=product, store=store, onec_series_id="")
        paid_n = Payment.objects.filter(order_id=oid, status=Payment.STATUS_PAID).count()
        self.assertLessEqual(paid_n, 1)
        if payment.status == Payment.STATUS_PAID:
            # Оплаченный заказ не должен остаться cancelled без needs_review/revive
            self.assertNotEqual(order.status, Order.STATUS_CANCELLED)
            self.assertEqual(stock.reserved_quantity, 1)
        elif order.status == Order.STATUS_CANCELLED:
            self.assertNotEqual(payment.status, Payment.STATUS_PAID)
            self.assertEqual(stock.reserved_quantity, 0)


@override_settings(SBER_ECOM_ENABLED=True)
class PostgresStockConcurrencyTests(TransactionTestCase):
    def setUp(self):
        _require_postgres()

    def test_last_non_serial_unit_single_winner(self):
        _order, product, store = _base_order(qty=1, reserved=0)
        Stock.objects.filter(store=store).update(quantity=1, reserved_quantity=0)

        outcomes: list[str] = []

        def worker():
            from django.db import transaction

            connections.close_all()
            try:
                with transaction.atomic():
                    plan_and_reserve_at_store(
                        product=product,
                        quantity=1,
                        price=Decimal("1000.00"),
                        store_id=store.pk,
                    )
                outcomes.append("ok")
            except InsufficientStockAtStore:
                outcomes.append("blocked")
            except Exception:  # noqa: BLE001
                outcomes.append("err")

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        stock = Stock.objects.get(product=product, store=store, onec_series_id="")
        self.assertEqual(stock.reserved_quantity, 1)
        self.assertEqual(outcomes.count("ok"), 1)

    def test_last_serial_unit_single_winner(self):
        series = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
        _order_a, product, store = _base_order(qty=1, reserved=0, series_id=series)
        Stock.objects.filter(store=store).delete()
        Stock.objects.create(
            product=product,
            store=store,
            quantity=1,
            reserved_quantity=0,
            onec_series_id=series,
            onec_series_name="S1",
        )

        outcomes: list[str] = []

        def worker():
            from django.db import transaction

            connections.close_all()
            try:
                with transaction.atomic():
                    plan_and_reserve_at_store(
                        product=product,
                        quantity=1,
                        price=Decimal("1000.00"),
                        store_id=store.pk,
                    )
                outcomes.append("ok")
            except InsufficientStockAtStore:
                outcomes.append("blocked")
            except Exception:  # noqa: BLE001
                outcomes.append("err")

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        stock = Stock.objects.get(product=product, store=store, onec_series_id=series)
        self.assertEqual(stock.reserved_quantity, 1)
        self.assertEqual(outcomes.count("ok"), 1)
