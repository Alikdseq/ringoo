"""BLOCK 4: completed→release, CLI apply lock, idempotency key length."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.orders.models import Order, OrderItem
from apps.orders.services.transitions import transition_order_status
from apps.products.models import Category, Product
from apps.stores.models import Stock, StockMovement, Store
from apps.stores.stock_ops import build_onec_import_idempotency_key
from integrations.onec.catalog_sync import (
    APPLY_LOCK_CACHE_KEY,
    _release_apply_lock,
    _try_acquire_apply_lock,
)
from tests.onec_test_utils import (
    TEST_RETAIL_WH_ID,
    ensure_confirmed_stores,
)


def _make_order_with_reserve(*, qty=2, reserved=2):
    ensure_confirmed_stores()
    store = Store.objects.get(onec_warehouse_id=TEST_RETAIL_WH_ID)
    cat = Category.objects.create(title="C", slug=f"b4-{timezone.now().timestamp()}")
    product = Product.objects.create(
        title="P",
        slug=f"b4-p-{product_slug_suffix()}",
        price=Decimal("100"),
        category=cat,
        is_active=True,
    )
    stock = Stock.objects.create(
        product=product,
        store=store,
        quantity=10,
        reserved_quantity=reserved,
        onec_series_id="",
    )
    order = Order.objects.create(
        full_name="T",
        phone="+7000",
        delivery_type=Order.DELIVERY_PICKUP,
        payment_type=Order.PAYMENT_CASH,
        store=store,
        status=Order.STATUS_READY,
        total_amount=Decimal("200"),
        consent_personal_data=True,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_title=product.title,
        quantity=qty,
        price=Decimal("100"),
        item_total=Decimal("100") * qty,
        onec_series_id="",
    )
    return order, stock, product, store


_slug_n = 0


def product_slug_suffix():
    global _slug_n
    _slug_n += 1
    return str(_slug_n)


class CompletedReleasesReserveTests(TestCase):
    def test_completed_releases_reserve_keeps_quantity(self):
        order, stock, _product, _store = _make_order_with_reserve(qty=2, reserved=2)
        transition_order_status(
            order,
            Order.STATUS_CLOSED,
            closure_result=Order.CLOSURE_COMPLETED,
            reason="test_complete",
        )
        stock.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CLOSED)
        self.assertEqual(order.closure_result, Order.CLOSURE_COMPLETED)
        self.assertEqual(stock.quantity, 10)
        self.assertEqual(stock.reserved_quantity, 0)

    def test_completed_twice_idempotent(self):
        order, stock, _p, _s = _make_order_with_reserve(qty=1, reserved=1)
        transition_order_status(order, Order.STATUS_CLOSED, closure_result=Order.CLOSURE_COMPLETED)
        transition_order_status(order, Order.STATUS_CLOSED, closure_result=Order.CLOSURE_COMPLETED)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(stock.quantity, 10)
        releases = StockMovement.objects.filter(
            idempotency_key__startswith=f"release:order:{order.pk}:",
            success=True,
        )
        self.assertEqual(releases.count(), 1)

    def test_cancel_releases_reserve(self):
        order, stock, _p, _s = _make_order_with_reserve(qty=2, reserved=2)
        with mock.patch("apps.orders.tasks.enqueue_order_cancel"):
            transition_order_status(
                order,
                Order.STATUS_CLOSED,
                closure_result=Order.CLOSURE_CANCELLED,
                skip_onec_cancel=True,
            )
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(stock.quantity, 10)

    def test_no_double_release_cancel_then_repeat(self):
        order, stock, _p, _s = _make_order_with_reserve(qty=1, reserved=1)
        with mock.patch("apps.orders.tasks.enqueue_order_cancel"):
            transition_order_status(
                order,
                "cancelled",
                skip_onec_cancel=True,
            )
            transition_order_status(
                order,
                Order.STATUS_CLOSED,
                closure_result=Order.CLOSURE_CANCELLED,
                skip_onec_cancel=True,
            )
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(
            StockMovement.objects.filter(
                idempotency_key=f"release:order:{order.pk}:item:" f"{order.items.get().pk}",
                success=True,
            ).count(),
            1,
        )


class IdempotencyKeyLengthTests(TestCase):
    def test_key_fixed_69_no_truncate_long_series(self):
        key = build_onec_import_idempotency_key("run-x", "prod", "store", "S" * 64)
        self.assertEqual(len(key), 69)
        self.assertTrue(key.startswith("onec:"))
        key2 = build_onec_import_idempotency_key("run-y", "prod", "store", "S" * 64)
        self.assertNotEqual(key, key2)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "onec-block4-lock",
        }
    }
)
class CliApplyLockTests(TestCase):
    def test_apply_uses_run_catalog_import_lock(self):
        import tempfile

        folders = (
            '<?xml version="1.0"?>'
            "<ПапкиНоменклатуры>"
            '<Папка code="F1" parentCode="" name="Phones"/>'
            "</ПапкиНоменклатуры>"
        )
        products = (
            '<?xml version="1.0"?>'
            "<Товары>"
            f'<Товар code="N1" parentCode="F1" name="P" price="10" quantity="1" '
            f'sklad="БАМ" skladID="{TEST_RETAIL_WH_ID}"/>'
            "</Товары>"
        )
        ensure_confirmed_stores()
        with tempfile.TemporaryDirectory() as tmp:
            fpath = Path(tmp) / "folders.xml"
            ppath = Path(tmp) / "products.xml"
            fpath.write_text(folders, encoding="utf-8")
            ppath.write_text(products, encoding="utf-8")
            held = _try_acquire_apply_lock("holder-run")
            self.assertTrue(held)
            try:
                with self.assertRaises(CommandError) as ctx:
                    call_command(
                        "import_onec_catalog",
                        "--folders",
                        str(fpath),
                        "--products",
                        str(ppath),
                        "--apply",
                        "--i-understand-apply",
                    )
                self.assertIn("Уже выполняется", str(ctx.exception))
            finally:
                _release_apply_lock("holder-run")

    def test_cli_apply_requires_confirm_flag(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("import_onec_catalog", "--from-api", "--apply")
        self.assertIn("i-understand-apply", str(ctx.exception))

    def test_dry_run_files_missing_errors(self):
        with self.assertRaises(CommandError):
            call_command(
                "import_onec_catalog",
                "--folders",
                str(Path("no-such-folders.xml")),
                "--products",
                str(Path("no-such-products.xml")),
            )
