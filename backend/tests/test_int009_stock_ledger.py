"""INT-009: журнал складских операций при release."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.orders.models import Order, OrderItem
from apps.orders.services import cancel_order_and_release_stock
from apps.products.models import Category, Product
from apps.stores.models import Stock, StockMovement, Store


class StockLedgerTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(title="C", slug="led-c")
        self.product = Product.objects.create(
            title="P", slug="led-p", price=Decimal("10"), category=cat, is_active=True
        )
        self.store = Store.objects.create(
            name="S", slug="led-s", address="a", city="c"
        )
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            reserved_quantity=2,
        )
        self.order = Order.objects.create(
            full_name="A",
            phone="79001110000",
            delivery_type=Order.DELIVERY_PICKUP,
            store=self.store,
            payment_type=Order.PAYMENT_CASH,
            status=Order.STATUS_NEW,
            total_amount=Decimal("20.00"),
            consent_personal_data=True,
        )
        self.item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_title=self.product.title,
            quantity=2,
            price=Decimal("10"),
            item_total=Decimal("20"),
        )

    def test_cancel_writes_release_ledger_once(self):
        cancel_order_and_release_stock(self.order, reason="test")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, 0)
        moves = StockMovement.objects.filter(
            order_id=self.order.pk, operation=StockMovement.OP_RELEASE
        )
        self.assertEqual(moves.count(), 1)
        # повторная отмена не дублирует release
        cancel_order_and_release_stock(self.order, reason="again")
        self.assertEqual(
            StockMovement.objects.filter(
                order_id=self.order.pk, operation=StockMovement.OP_RELEASE
            ).count(),
            1,
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, 0)
