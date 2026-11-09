"""Возвраты: создание, частичный, dry_run money, restock только sellable."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.products.models import Category, Product, ProductColor
from apps.returns.models import ReturnItem, ReturnRequest
from apps.returns.services import (
    create_return_request,
    initiate_money_refund,
    inspect_and_maybe_restock,
    transition_return,
)
from apps.stores.models import Stock, StockMovement, Store

User = get_user_model()


@override_settings(ADMIN_OTP_ENABLED=False)
class ReturnFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+79002223344", password="pass")
        self.admin = User.objects.create_user(
            phone="+79002223355", password="pass", is_staff=True, is_superuser=True
        )
        cat = Category.objects.create(title="C", slug="c-ret")
        self.product = Product.objects.create(
            title="Phone", slug="phone-ret", price=Decimal("1000.00"), category=cat
        )
        self.color = ProductColor.objects.create(
            product=self.product, slug="black", label="Чёрный", hex="#000"
        )
        self.store = Store.objects.create(
            name="S", slug="s-ret", address="a", city="Москва", is_active=True
        )
        Stock.objects.create(product=self.product, store=self.store, quantity=5)
        self.order = Order.objects.create(
            user=self.user,
            order_number="ORD-RET-1",
            full_name="A",
            phone="+79002223344",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_ONLINE,
            status=Order.STATUS_COMPLETED,
            store=self.store,
            total_amount=Decimal("3000.00"),
        )
        self.oi = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_title="Phone",
            quantity=3,
            price=Decimal("1000.00"),
            item_total=Decimal("3000.00"),
            color=self.color,
            color_label="Чёрный",
            color_slug="black",
        )
        self.payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("3000.00"),
            amount_kopecks=300000,
            merchant_order_number="ret-mo-1",
            status=Payment.STATUS_PAID,
            provider="yookassa",
            yookassa_payment_id="yk-ret-1",
        )

    def test_partial_return_and_double_qty_blocked(self):
        rr = create_return_request(
            order=self.order,
            user=self.user,
            ground=ReturnRequest.GROUND_QUALITY_OK,
            demand=ReturnRequest.DEMAND_REFUND,
            description="не подошёл",
            items=[{"order_item_id": self.oi.pk, "quantity": 1}],
        )
        self.assertEqual(rr.requested_refund_amount, Decimal("1000.00"))
        with self.assertRaises(ValueError):
            create_return_request(
                order=self.order,
                user=self.user,
                ground=ReturnRequest.GROUND_QUALITY_OK,
                demand=ReturnRequest.DEMAND_REFUND,
                description="ещё",
                items=[{"order_item_id": self.oi.pk, "quantity": 3}],
            )

    def test_money_dry_run_idempotent_and_cap(self):
        rr = create_return_request(
            order=self.order,
            user=self.user,
            ground=ReturnRequest.GROUND_QUALITY_OK,
            demand=ReturnRequest.DEMAND_REFUND,
            description="x",
            items=[{"order_item_id": self.oi.pk, "quantity": 1}],
        )
        transition_return(rr, ReturnRequest.STATUS_UNDER_REVIEW, actor=self.admin)
        transition_return(rr, ReturnRequest.STATUS_APPROVED, actor=self.admin)
        mr1 = initiate_money_refund(rr, dry_run=True, actor=self.admin)
        mr2 = initiate_money_refund(rr, dry_run=True, actor=self.admin)
        self.assertEqual(mr1.pk, mr2.pk)
        self.assertEqual(mr1.status, mr1.STATUS_NEEDS_REVIEW)

    def test_restock_only_sellable(self):
        rr = create_return_request(
            order=self.order,
            user=self.user,
            ground=ReturnRequest.GROUND_DEFECT,
            demand=ReturnRequest.DEMAND_REFUND,
            description="брак",
            items=[{"order_item_id": self.oi.pk, "quantity": 1}],
        )
        for st in (
            ReturnRequest.STATUS_UNDER_REVIEW,
            ReturnRequest.STATUS_APPROVED,
            ReturnRequest.STATUS_AWAITING_SHIPMENT,
            ReturnRequest.STATUS_IN_TRANSIT,
            ReturnRequest.STATUS_RECEIVED,
            ReturnRequest.STATUS_INSPECTION,
        ):
            transition_return(rr, st, actor=self.admin)
            rr.refresh_from_db()
        item = rr.items.get()
        stock_before = Stock.objects.get(product=self.product, store=self.store).quantity
        inspect_and_maybe_restock(
            rr,
            item_updates=[
                {
                    "return_item_id": item.pk,
                    "condition": ReturnItem.CONDITION_DEFECTIVE,
                    "restock_qty": 0,
                }
            ],
            actor=self.admin,
            store_id=self.store.pk,
        )
        self.assertEqual(
            Stock.objects.get(product=self.product, store=self.store).quantity,
            stock_before,
        )
        # sellable restock
        rr2 = create_return_request(
            order=self.order,
            user=self.user,
            ground=ReturnRequest.GROUND_QUALITY_OK,
            demand=ReturnRequest.DEMAND_REFUND,
            description="ok",
            items=[{"order_item_id": self.oi.pk, "quantity": 1}],
        )
        for st in (
            ReturnRequest.STATUS_UNDER_REVIEW,
            ReturnRequest.STATUS_APPROVED,
            ReturnRequest.STATUS_AWAITING_SHIPMENT,
            ReturnRequest.STATUS_IN_TRANSIT,
            ReturnRequest.STATUS_RECEIVED,
            ReturnRequest.STATUS_INSPECTION,
        ):
            transition_return(rr2, st, actor=self.admin)
            rr2.refresh_from_db()
        item2 = rr2.items.get()
        inspect_and_maybe_restock(
            rr2,
            item_updates=[
                {
                    "return_item_id": item2.pk,
                    "condition": ReturnItem.CONDITION_SELLABLE,
                    "restock_qty": 1,
                }
            ],
            actor=self.admin,
            store_id=self.store.pk,
        )
        self.assertEqual(
            Stock.objects.get(product=self.product, store=self.store).quantity,
            stock_before + 1,
        )
        self.assertTrue(
            StockMovement.objects.filter(
                operation=StockMovement.OP_RESTOCK, success=True
            ).exists()
        )

    @override_settings(RETURNS_ENABLED=True)
    def test_customer_api_create(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.post(
            "/api/v1/returns/create/",
            {
                "order_id": str(self.order.pk),
                "ground": "quality_ok",
                "demand": "refund_money",
                "description": "тест",
                "return_method": "carrier",
                "items": [{"order_item_id": str(self.oi.pk), "quantity": 1}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    @override_settings(RETURNS_ENABLED=False)
    def test_customer_api_disabled(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.post(
            "/api/v1/returns/create/",
            {
                "order_id": str(self.order.pk),
                "ground": "quality_ok",
                "demand": "refund_money",
                "description": "тест",
                "return_method": "carrier",
                "items": [{"order_item_id": str(self.oi.pk), "quantity": 1}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data.get("code"), "returns_temporarily_disabled")
        list_resp = client.get("/api/v1/returns/")
        self.assertEqual(list_resp.status_code, 403)
        self.assertEqual(list_resp.data.get("code"), "returns_temporarily_disabled")
