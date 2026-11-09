"""INV-001: отрицательные цена и количество из XML 1С не перезаписывают каталог."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.products.models import Category, Product
from apps.stores.models import Stock, Store
from integrations.onec.catalog_sync import run_catalog_import
from integrations.onec.importer import (
    ImportMode,
    apply_catalog_import,
    plan_catalog_import_from_xml_strings,
)


FOLDERS = '<ПапкиНоменклатуры><Папка code="F1" parentCode="" name="Phones"/></ПапкиНоменклатуры>'


def _xml(*rows: str) -> str:
    return "<Товары>" + "".join(rows) + "</Товары>"


def _row(code, price, qty, name="Phone"):
    return (
        f'<Товар code="{code}" parentCode="F1" name="{name}" '
        f'price="{price}" quantity="{qty}" sklad="Main" skladID="WH9"/>'
    )


class CatalogGuardTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title="Old", slug="old-cat", onec_code="F1")
        self.product = Product.objects.create(
            title="Old phone",
            slug="old-phone",
            sku="N-OLD",
            onec_code="N-OLD",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )
        self.store = Store.objects.create(
            name="Main",
            slug="wh9",
            address="a",
            city="c",
            onec_warehouse_id="WH9",
        )
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=7,
            reserved_quantity=2,
        )

    def _plan(self, products_xml):
        return plan_catalog_import_from_xml_strings(
            FOLDERS, products_xml, mode=ImportMode.DRY_RUN
        )

    def test_negative_price_and_qty_do_not_overwrite_on_apply(self):
        plan = self._plan(_xml(_row("N-OLD", "-10", "-3")))
        rejected = [i for i in plan.issues if i.get("type") in ("rejected_price", "rejected_quantity")]
        self.assertGreaterEqual(len(rejected), 2)
        price_issue = next(i for i in rejected if i["field"] == "price")
        qty_issue = next(i for i in rejected if i["field"] == "quantity")
        self.assertEqual(price_issue["onec_code"], "N-OLD")
        self.assertEqual(price_issue["value"], "-10")
        self.assertEqual(price_issue["reason"], "negative")
        self.assertEqual(qty_issue["reason"], "negative")
        self.assertEqual(plan.summary["rejected_positions"], 2)
        before_products = Product.objects.count()
        plan.mode = ImportMode.APPLY.value
        apply_catalog_import(plan)
        self.product.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(Product.objects.count(), before_products)
        self.assertEqual(self.product.price, Decimal("100.00"))
        self.assertEqual(self.stock.quantity, 7)
        self.assertEqual(self.stock.reserved_quantity, 2)

    def test_dry_run_reports_rejection_and_does_not_write(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            folders = Path(tmp) / "folders.xml"
            products = Path(tmp) / "products.xml"
            folders.write_text(FOLDERS, encoding="utf-8")
            products.write_text(_xml(_row("N-OLD", "-1", "1")), encoding="utf-8")
            result = run_catalog_import(
                dry_run=True,
                from_api=False,
                folders_path=str(folders),
                products_path=str(products),
            )
        self.assertTrue(result["dry_run"])
        self.assertGreaterEqual(result["summary"].get("rejected_positions", 0), 1)
        price_rows = [
            row
            for row in result["error_messages"]
            if row.get("field") == "price" and row.get("onec_code") == "N-OLD"
        ]
        self.assertEqual(price_rows[0]["reason"], "negative")
        self.assertEqual(price_rows[0]["value"], "-1")
        self.product.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("100.00"))
        self.assertEqual(self.stock.quantity, 7)

    def test_zero_price_and_zero_stock_are_explicit(self):
        plan = self._plan(_xml(_row("N-OLD", "0", "0")))
        self.assertFalse(any(i.get("reason") == "negative" for i in plan.issues))
        stock = next(s for s in plan.stocks if s.onec_code == "N-OLD")
        self.assertEqual(stock.action, "upsert")
        self.assertEqual(stock.quantity_status, "explicit_zero")
        product_action = next(p for p in plan.products if p.onec_code == "N-OLD")
        self.assertEqual(product_action.action, "update")
        self.assertEqual(product_action.price, "0")
        plan.mode = ImportMode.APPLY.value
        apply_catalog_import(plan)
        self.product.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("0.00"))
        self.assertEqual(self.stock.quantity, 0)
        self.assertEqual(self.stock.reserved_quantity, 2)

    def test_empty_price_and_garbage_and_overflow_and_precision(self):
        plan = self._plan(
            _xml(
                _row("N-OLD", "", "2"),
                _row("N-BAD", "abc", "x"),
                _row("N-BIG", "10000000000.00", "2147483648"),
                _row("N-PREC", "10.999", "1.5"),
                _row("N-OK", "15.50", "4"),
            )
        )
        reasons = {(i.get("onec_code"), i.get("field"), i.get("reason")) for i in plan.issues}
        self.assertIn(("N-OLD", "price", "empty"), reasons)
        self.assertIn(("N-BAD", "price", "not_a_number"), reasons)
        self.assertIn(("N-BAD", "quantity", "not_a_number"), reasons)
        self.assertIn(("N-BIG", "price", "overflow"), reasons)
        self.assertIn(("N-BIG", "quantity", "overflow"), reasons)
        self.assertIn(("N-PREC", "price", "precision"), reasons)
        self.assertIn(("N-PREC", "quantity", "not_integer"), reasons)
        ok = next(p for p in plan.products if p.onec_code == "N-OK")
        self.assertEqual(ok.action, "create")
        bad = next(p for p in plan.products if p.onec_code == "N-BAD")
        self.assertEqual(bad.action, "skip")
        plan.mode = ImportMode.APPLY.value
        apply_catalog_import(plan)
        self.product.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("100.00"))
        self.assertEqual(self.stock.quantity, 7)
        created = Product.objects.get(onec_code="N-OK")
        self.assertEqual(created.price, Decimal("15.50"))
        self.assertFalse(Product.objects.filter(onec_code="N-BAD").exists())
        self.assertFalse(Product.objects.filter(onec_code="N-PREC").exists())
        self.assertFalse(Product.objects.filter(onec_code="N-BIG").exists())

    def test_good_row_beside_bad_row_updates_only_the_good_one(self):
        other = Product.objects.create(
            title="Other",
            slug="other-phone",
            onec_code="N-GOOD",
            price=Decimal("50.00"),
            category=self.category,
        )
        Stock.objects.create(product=other, store=self.store, quantity=3, reserved_quantity=1)
        plan = self._plan(
            _xml(
                _row("N-OLD", "-5", "9"),
                _row("N-GOOD", "80.00", "6", name="Other"),
            )
        )
        plan.mode = ImportMode.APPLY.value
        apply_catalog_import(plan)
        self.product.refresh_from_db()
        self.stock.refresh_from_db()
        other.refresh_from_db()
        good_stock = Stock.objects.get(product=other, store=self.store)
        self.assertEqual(self.product.price, Decimal("100.00"))
        self.assertEqual(self.stock.quantity, 7)
        self.assertEqual(other.price, Decimal("80.00"))
        self.assertEqual(good_stock.quantity, 6)
        self.assertEqual(good_stock.reserved_quantity, 1)
