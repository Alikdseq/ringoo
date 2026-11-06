"""Цвет ↔ 1С: matched onec_code влияет на productCode; series ≠ color."""

from decimal import Decimal

from django.test import TestCase

from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product, ProductColor
from apps.stores.models import Store
from integrations.onec.orders import build_order_items_payload


class ColorOnecMappingTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(title="C", slug="c-map")
        self.product = Product.objects.create(
            title="P",
            slug="p-map",
            price=Decimal("10"),
            category=cat,
            onec_code="PROD-1",
        )
        self.color = ProductColor.objects.create(
            product=self.product,
            slug="black",
            label="Black",
            onec_code="PROD-1-BLACK",
            mapping_status=ProductColor.MAPPING_MATCHED,
        )
        store = Store.objects.create(
            name="S", slug="s-map", address="a", city="Москва", is_active=True
        )
        self.order = Order.objects.create(
            order_number="ORD-MAP-1",
            full_name="A",
            phone="+79001112233",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            status=Order.STATUS_NEW,
            store=store,
            total_amount=Decimal("10"),
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_title="P",
            quantity=1,
            price=Decimal("10"),
            item_total=Decimal("10"),
            color=self.color,
            color_label="Black",
            color_slug="black",
            onec_product_code="PROD-1",
            onec_series_id="",
        )

    def test_matched_color_code_used(self):
        payload = build_order_items_payload(self.order)
        self.assertEqual(payload[0]["productCode"], "PROD-1-BLACK")
        self.assertEqual(payload[0]["colorLabel"], "Black")
        self.assertIsNone(payload[0]["seriesId"])

    def test_unmatched_falls_back_to_item_code(self):
        self.color.mapping_status = ProductColor.MAPPING_UNMATCHED
        self.color.save()
        payload = build_order_items_payload(self.order)
        self.assertEqual(payload[0]["productCode"], "PROD-1")
