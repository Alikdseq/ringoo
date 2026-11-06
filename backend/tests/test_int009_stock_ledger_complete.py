"""INT-009 complete: checkout reserve, admin correction, 1C upsert, delivery net."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.test import TestCase

from apps.products.models import Category, Product
from apps.stores.models import Stock, StockMovement, Store
from apps.stores.stock_ops import (
    apply_onec_stock_upsert,
    apply_quantity_correction,
    release_for_delivery,
    reserve_for_delivery,
)
from integrations.onec.orders import plan_and_reserve_at_store


class StockLedgerCompleteTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(title="C", slug="slc-c")
        self.product = Product.objects.create(
            title="P", slug="slc-p", price=Decimal("10"), category=cat, is_active=True
        )
        self.store = Store.objects.create(
            name="S", slug="slc-s", address="a", city="c"
        )
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=10,
            reserved_quantity=0,
        )

    def test_checkout_reserve_writes_ledger(self):
        with transaction.atomic():
            plan_and_reserve_at_store(
                product=self.product,
                quantity=2,
                price=Decimal("10"),
                store_id=self.store.pk,
            )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, 2)
        self.assertTrue(
            StockMovement.objects.filter(
                product_id=self.product.pk,
                operation=StockMovement.OP_RESERVE,
                success=True,
            ).exists()
        )

    def test_admin_correction_ledger(self):
        apply_quantity_correction(
            self.stock, new_quantity=7, new_reserved=1, reason="admin_test"
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 7)
        self.assertEqual(self.stock.reserved_quantity, 1)
        move = StockMovement.objects.get(operation=StockMovement.OP_CORRECTION)
        self.assertEqual(move.stock_quantity_after, 7)

    def test_onec_upsert_reconciliation(self):
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="",
            series_name="",
            quantity=42,
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 42)
        self.assertTrue(
            StockMovement.objects.filter(
                operation=StockMovement.OP_RECONCILIATION, success=True
            ).exists()
        )
        # idempotent same qty
        apply_onec_stock_upsert(
            product_id=self.product.pk,
            store_id=self.store.pk,
            series_id="",
            series_name="",
            quantity=42,
        )
        self.assertEqual(
            StockMovement.objects.filter(
                operation=StockMovement.OP_RECONCILIATION
            ).count(),
            1,
        )

    def test_delivery_network_reserve_release(self):
        ok = reserve_for_delivery(
            self.product.pk, 3, idempotency_key="del-res-1", reason="delivery"
        )
        self.assertTrue(ok)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, 3)
        ok2 = release_for_delivery(
            self.product.pk, 3, idempotency_key="del-rel-1", reason="delivery"
        )
        self.assertTrue(ok2)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, 0)
