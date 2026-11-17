"""RELEASE 46.1 Stage B: present_only default vs full_snapshot + CLI dual confirm."""

from __future__ import annotations

import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.products.models import Category, Product
from apps.stores.models import Stock
from integrations.onec.catalog_sync import run_catalog_import
from integrations.onec.importer import (
    ImportMode,
    SnapshotPolicy,
    normalize_snapshot_policy,
    plan_catalog_import,
    plan_catalog_import_from_xml_strings,
    plan_from_parsed,
)
from tests.onec_plan_apply_helpers import persist_and_apply_for_tests
from integrations.onec.parser import parse_catalog_xml_strings
from tests.onec_test_utils import (
    TEST_OTHER_WH_ID,
    TEST_RETAIL_WH_ID,
    TEST_RETAIL_WH_NAME,
    ensure_confirmed_stores,
)

FOLDERS = (
    '<ПапкиНоменклатуры><Папка code="F1" parentCode="" name="Phones"/>'
    "</ПапкиНоменклатуры>"
)


def _xml(*rows: str) -> str:
    return "<Товары>" + "".join(rows) + "</Товары>"


def _row(
    code: str,
    price: str,
    qty: str | int,
    *,
    name: str = "Phone",
    sklad: str = TEST_RETAIL_WH_NAME,
    sklad_id: str = TEST_RETAIL_WH_ID,
    series: str = "",
    series_id: str = "",
) -> str:
    extra = ""
    if series or series_id:
        extra = f' series="{series}" seriesID="{series_id}"'
    return (
        f'<Товар code="{code}" parentCode="F1" name="{name}" '
        f'price="{price}" quantity="{qty}" sklad="{sklad}" skladID="{sklad_id}"'
        f"{extra}/>"
    )


class NormalizeSnapshotPolicyTests(TestCase):
    def test_default_none_and_empty(self):
        self.assertEqual(normalize_snapshot_policy(None), "present_only")
        self.assertEqual(normalize_snapshot_policy(""), "present_only")

    def test_enum_and_strings(self):
        self.assertEqual(
            normalize_snapshot_policy(SnapshotPolicy.FULL_SNAPSHOT), "full_snapshot"
        )
        self.assertEqual(normalize_snapshot_policy("present_only"), "present_only")
        self.assertEqual(normalize_snapshot_policy("full_snapshot"), "full_snapshot")

    def test_unknown_raises(self):
        with self.assertRaises(ValueError) as ctx:
            normalize_snapshot_policy("partial")
        self.assertIn("Unknown snapshot_policy", str(ctx.exception))


class PresentOnlyMissingProductTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="po-c", onec_code="F1")
        self.product = Product.objects.create(
            title="Keep",
            slug="po-keep",
            sku="N-KEEP",
            onec_code="N-KEEP",
            price=Decimal("100"),
            category=self.cat,
            is_active=True,
        )
        self.store = self.stores[TEST_RETAIL_WH_ID]
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=9,
            reserved_quantity=3,
            onec_series_id="",
        )
        Product.objects.create(
            title="Other",
            slug="po-other",
            onec_code="N-OTHER",
            price=Decimal("50"),
            category=self.cat,
        )

    def test_missing_product_not_zeroed_present_only(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-OTHER", "50", 1, name="Other")),
            mode=ImportMode.APPLY,
        )
        self.assertEqual(plan.snapshot_policy, SnapshotPolicy.PRESENT_ONLY.value)
        self.assertEqual(plan.stocks_to_zero, [])
        self.assertEqual(plan.summary.get("stocks_to_zero"), 0)
        persist_and_apply_for_tests(plan)
        self.product.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertTrue(Stock.objects.filter(pk=self.stock.pk).exists())
        self.assertEqual(self.stock.quantity, 9)
        self.assertEqual(self.stock.reserved_quantity, 3)


class PresentOnlyMissingSeriesTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="ps-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="ps-p",
            onec_code="N-SER",
            price=Decimal("100"),
            category=self.cat,
        )
        self.store = self.stores[TEST_RETAIL_WH_ID]
        self.keep = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=2,
            reserved_quantity=1,
            onec_series_id="ser-keep",
            onec_series_name="K",
        )
        self.gone = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            reserved_quantity=2,
            onec_series_id="ser-gone",
            onec_series_name="G",
        )

    def test_missing_series_preserved(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-SER", "100", 8, series="K", series_id="ser-keep")),
            mode=ImportMode.APPLY,
        )
        self.assertEqual(plan.stocks_to_zero, [])
        persist_and_apply_for_tests(plan)
        self.keep.refresh_from_db()
        self.gone.refresh_from_db()
        self.assertEqual(self.keep.quantity, 8)
        self.assertEqual(self.keep.reserved_quantity, 1)
        self.assertEqual(self.gone.quantity, 5)
        self.assertEqual(self.gone.reserved_quantity, 2)


class FullSnapshotZeroPlanTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="fs-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="fs-p",
            onec_code="N-FS",
            price=Decimal("100"),
            category=self.cat,
        )
        self.store_a = self.stores[TEST_RETAIL_WH_ID]
        self.store_b = self.stores[TEST_OTHER_WH_ID]
        self.stock_a = Stock.objects.create(
            product=self.product,
            store=self.store_a,
            quantity=4,
            reserved_quantity=1,
            onec_series_id="",
        )
        self.stock_b = Stock.objects.create(
            product=self.product,
            store=self.store_b,
            quantity=7,
            reserved_quantity=2,
            onec_series_id="",
        )

    def test_full_snapshot_plans_zero_for_missing(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-FS", "100", 3)),
            mode=ImportMode.DRY_RUN,
            snapshot_policy=SnapshotPolicy.FULL_SNAPSHOT.value,
        )
        self.assertEqual(plan.snapshot_policy, SnapshotPolicy.FULL_SNAPSHOT.value)
        zero_keys = {
            (z.site_product_id, z.site_store_id, (z.series_id or "").strip())
            for z in plan.stocks_to_zero
            if z.action == "zero"
        }
        self.assertIn(
            (str(self.product.pk), str(self.store_b.pk), ""),
            zero_keys,
        )
        self.assertNotIn(
            (str(self.product.pk), str(self.store_a.pk), ""),
            zero_keys,
        )
        plan.mode = ImportMode.APPLY.value
        persist_and_apply_for_tests(plan)
        self.stock_a.refresh_from_db()
        self.stock_b.refresh_from_db()
        self.assertEqual(self.stock_a.quantity, 3)
        self.assertEqual(self.stock_a.reserved_quantity, 1)
        self.assertEqual(self.stock_b.quantity, 0)
        self.assertEqual(self.stock_b.reserved_quantity, 2)


class DefaultPresentOnlyEntryPointsTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="def-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="def-p",
            onec_code="N-DEF",
            price=Decimal("10"),
            category=self.cat,
        )
        Stock.objects.create(
            product=self.product,
            store=self.stores[TEST_RETAIL_WH_ID],
            quantity=11,
            reserved_quantity=4,
        )
        Product.objects.create(
            title="X",
            slug="def-x",
            onec_code="N-X",
            price=Decimal("1"),
            category=self.cat,
        )
        self.products_xml = _xml(_row("N-X", "1", 1, name="X"))

    def test_plan_from_parsed_default(self):
        parsed = parse_catalog_xml_strings(FOLDERS, self.products_xml)
        plan = plan_from_parsed(parsed)
        self.assertEqual(plan.snapshot_policy, "present_only")
        self.assertEqual(plan.stocks_to_zero, [])

    def test_plan_from_xml_strings_default(self):
        plan = plan_catalog_import_from_xml_strings(FOLDERS, self.products_xml)
        self.assertEqual(plan.snapshot_policy, "present_only")
        self.assertEqual(plan.stocks_to_zero, [])

    def test_plan_catalog_import_files_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "folders.xml"
            pp = Path(tmp) / "products.xml"
            fp.write_text(FOLDERS, encoding="utf-8")
            pp.write_text(self.products_xml, encoding="utf-8")
            plan = plan_catalog_import(fp, pp)
            self.assertEqual(plan.snapshot_policy, "present_only")
            self.assertEqual(plan.stocks_to_zero, [])

    def test_run_catalog_import_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "folders.xml"
            pp = Path(tmp) / "products.xml"
            fp.write_text(FOLDERS, encoding="utf-8")
            pp.write_text(self.products_xml, encoding="utf-8")
            data = run_catalog_import(
                dry_run=True,
                from_api=False,
                folders_path=str(fp),
                products_path=str(pp),
            )
            summary = data.get("summary") or {}
            self.assertEqual(summary.get("snapshot_policy"), "present_only")
            self.assertEqual(int(summary.get("stocks_to_zero") or 0), 0)
            self.assertEqual(int(summary.get("planned_stocks_to_zero") or 0), 0)


class UnknownPolicyNoWriteTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="unk-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="unk-p",
            onec_code="N-UNK",
            price=Decimal("10"),
            category=self.cat,
        )
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.stores[TEST_RETAIL_WH_ID],
            quantity=6,
            reserved_quantity=2,
        )

    def test_unknown_policy_raises_no_db_change(self):
        with self.assertRaises(ValueError):
            plan_catalog_import_from_xml_strings(
                FOLDERS,
                _xml(_row("N-UNK", "10", 1)),
                snapshot_policy="weird",
            )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 6)
        self.assertEqual(self.stock.reserved_quantity, 2)

    def test_run_catalog_import_unknown_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "folders.xml"
            pp = Path(tmp) / "products.xml"
            fp.write_text(FOLDERS, encoding="utf-8")
            pp.write_text(_xml(_row("N-UNK", "10", 1)), encoding="utf-8")
            with self.assertRaises(ValueError):
                run_catalog_import(
                    dry_run=True,
                    from_api=False,
                    folders_path=str(fp),
                    products_path=str(pp),
                    snapshot_policy="nope",
                )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 6)
        self.assertEqual(self.stock.reserved_quantity, 2)


class PresentOnlyIdempotencyTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="id-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="id-p",
            onec_code="N-ID",
            price=Decimal("10"),
            category=self.cat,
        )
        self.store = self.stores[TEST_RETAIL_WH_ID]
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.store,
            quantity=3,
            reserved_quantity=1,
            onec_series_id="",
        )

    def test_double_import_present_only(self):
        xml = _xml(_row("N-ID", "10", 3))
        for _ in range(2):
            plan = plan_catalog_import_from_xml_strings(
                FOLDERS, xml, mode=ImportMode.APPLY
            )
            self.assertEqual(plan.stocks_to_zero, [])
            persist_and_apply_for_tests(plan)
        self.assertEqual(
            Stock.objects.filter(product=self.product, store=self.store).count(), 1
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 3)
        self.assertEqual(self.stock.reserved_quantity, 1)
        self.assertEqual(Product.objects.filter(onec_code="N-ID").count(), 1)


class PresentOnlyRegressionTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="rg-c", onec_code="F1")
        self.store = self.stores[TEST_RETAIL_WH_ID]

    def test_create_update_multi_series_prices(self):
        # create
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(
                _row("N-NEW", "12.50", 2, name="NewPhone", series="A", series_id="s-a"),
                _row("N-NEW", "12.50", 4, name="NewPhone", series="B", series_id="s-b"),
            ),
            mode=ImportMode.APPLY,
        )
        self.assertTrue(plan.apply_allowed, plan.apply_blockers)
        self.assertEqual(plan.stocks_to_zero, [])
        persist_and_apply_for_tests(plan)
        product = Product.objects.get(onec_code="N-NEW")
        self.assertEqual(product.price, Decimal("12.50"))
        self.assertEqual(
            Stock.objects.filter(product=product, store=self.store).count(), 2
        )
        # update + keep other series untouched when present_only
        Stock.objects.create(
            product=product,
            store=self.store,
            quantity=9,
            reserved_quantity=1,
            onec_series_id="s-orphan",
            onec_series_name="O",
        )
        plan2 = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(
                _row("N-NEW", "15.00", 5, name="NewPhone2", series="A", series_id="s-a"),
            ),
            mode=ImportMode.APPLY,
        )
        persist_and_apply_for_tests(plan2)
        product.refresh_from_db()
        self.assertEqual(product.title, "NewPhone2")
        self.assertEqual(product.price, Decimal("15.00"))
        sa = Stock.objects.get(product=product, store=self.store, onec_series_id="s-a")
        sb = Stock.objects.get(product=product, store=self.store, onec_series_id="s-b")
        so = Stock.objects.get(
            product=product, store=self.store, onec_series_id="s-orphan"
        )
        self.assertEqual(sa.quantity, 5)
        self.assertEqual(sb.quantity, 4)
        self.assertEqual(so.quantity, 9)
        self.assertEqual(so.reserved_quantity, 1)


class CliSnapshotPolicyTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="cli-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="cli-p",
            onec_code="N-CLI",
            price=Decimal("10"),
            category=self.cat,
        )
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.stores[TEST_RETAIL_WH_ID],
            quantity=8,
            reserved_quantity=3,
        )
        Product.objects.create(
            title="Other",
            slug="cli-o",
            onec_code="N-CLI-O",
            price=Decimal("1"),
            category=self.cat,
        )

    def _write_xml(self, tmp: str) -> tuple[str, str]:
        fp = Path(tmp) / "folders.xml"
        pp = Path(tmp) / "products.xml"
        fp.write_text(FOLDERS, encoding="utf-8")
        pp.write_text(_xml(_row("N-CLI-O", "1", 1, name="Other")), encoding="utf-8")
        return str(fp), str(pp)

    def test_default_cli_present_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folders, products = self._write_xml(tmp)
            out = StringIO()
            call_command(
                "import_onec_catalog",
                "--folders",
                folders,
                "--products",
                products,
                "--report",
                str(Path(tmp) / "report.json"),
                stdout=out,
            )
            text = out.getvalue()
            self.assertIn("snapshot_policy=present_only", text)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.assertEqual(self.stock.reserved_quantity, 3)

    def test_full_snapshot_without_ack_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folders, products = self._write_xml(tmp)
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "import_onec_catalog",
                    "--folders",
                    folders,
                    "--products",
                    products,
                    "--full-snapshot",
                )
            self.assertIn("i-understand-full-snapshot", str(ctx.exception))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.assertEqual(self.stock.reserved_quantity, 3)

    def test_ack_without_full_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folders, products = self._write_xml(tmp)
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "import_onec_catalog",
                    "--folders",
                    folders,
                    "--products",
                    products,
                    "--i-understand-full-snapshot",
                )
            self.assertIn("без --full-snapshot", str(ctx.exception))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)

    def test_full_snapshot_dry_run_with_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            folders, products = self._write_xml(tmp)
            out = StringIO()
            call_command(
                "import_onec_catalog",
                "--folders",
                folders,
                "--products",
                products,
                "--full-snapshot",
                "--i-understand-full-snapshot",
                "--report",
                str(Path(tmp) / "report.json"),
                stdout=out,
            )
            text = out.getvalue()
            self.assertIn("snapshot_policy=full_snapshot", text)
            self.assertIn("stocks_to_zero=", text)
        # dry-run: no write
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.assertEqual(self.stock.reserved_quantity, 3)

    def test_apply_still_requires_confirm(self):
        with tempfile.TemporaryDirectory() as tmp:
            folders, products = self._write_xml(tmp)
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "import_onec_catalog",
                    "--folders",
                    folders,
                    "--products",
                    products,
                    "--apply",
                )
            self.assertIn("i-understand-apply", str(ctx.exception))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)

    def test_apply_full_snapshot_needs_four_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            folders, products = self._write_xml(tmp)
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "import_onec_catalog",
                    "--folders",
                    folders,
                    "--products",
                    products,
                    "--full-snapshot",
                    "--i-understand-full-snapshot",
                    "--apply",
                )
            msg = str(ctx.exception)
            self.assertTrue(
                "i-understand-apply" in msg or "четыре флага" in msg,
                msg,
            )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.assertEqual(self.stock.reserved_quantity, 3)

    def test_present_only_apply_does_not_zero_missing(self):
        import json

        with tempfile.TemporaryDirectory() as tmp:
            folders, products = self._write_xml(tmp)
            dry_report = str(Path(tmp) / "dry.json")
            call_command(
                "import_onec_catalog",
                "--folders",
                folders,
                "--products",
                products,
                "--report",
                dry_report,
            )
            dry = json.loads(Path(dry_report).read_text(encoding="utf-8"))
            plan_id = dry["plan_id"]
            call_command(
                "import_onec_catalog",
                "--apply",
                "--plan-id",
                plan_id,
                "--i-understand-apply",
                "--report",
                str(Path(tmp) / "report.json"),
            )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.assertEqual(self.stock.reserved_quantity, 3)


class ApplyDefensePresentOnlyZerosTests(TestCase):
    """Defense: apply refuses stocks_to_zero under present_only policy."""

    def setUp(self):
        self.stores = ensure_confirmed_stores()
        self.cat = Category.objects.create(title="C", slug="defz-c", onec_code="F1")
        self.product = Product.objects.create(
            title="P",
            slug="defz-p",
            onec_code="N-DEFZ",
            price=Decimal("10"),
            category=self.cat,
        )
        self.stock = Stock.objects.create(
            product=self.product,
            store=self.stores[TEST_RETAIL_WH_ID],
            quantity=4,
            reserved_quantity=1,
        )

    def test_apply_rejects_injected_zeros_on_present_only_plan(self):
        from integrations.onec.importer import StockAction

        plan = plan_catalog_import_from_xml_strings(
            FOLDERS,
            _xml(_row("N-DEFZ", "10", 4)),
            mode=ImportMode.APPLY,
        )
        self.assertEqual(plan.snapshot_policy, "present_only")
        plan.stocks_to_zero = [
            StockAction(
                onec_code="N-DEFZ",
                sklad="",
                sklad_id=TEST_RETAIL_WH_ID,
                quantity="0",
                quantity_status="zeroed",
                action="zero",
                site_product_id=str(self.product.pk),
                site_store_id=str(self.stores[TEST_RETAIL_WH_ID].pk),
            )
        ]
        with self.assertRaises(Exception) as ctx:
            persist_and_apply_for_tests(plan)
        msg = str(ctx.exception).lower()
        self.assertTrue(
            "full_snapshot" in msg or "stocks_to_zero" in msg or "present_only" in msg,
            msg,
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 4)
        self.assertEqual(self.stock.reserved_quantity, 1)


class FetchAndPlanApiPolicyTests(TestCase):
    def setUp(self):
        ensure_confirmed_stores()
        Category.objects.create(title="C", slug="api-c", onec_code="F1")

    def test_fetch_and_plan_default_present_only(self):
        from integrations.onec.importer import fetch_and_plan_from_api

        class FakeClient:
            base_url = "http://test.local/"

            def fetch_folders_xml(self):
                return FOLDERS

            def fetch_products_xml(self):
                return _xml(_row("N-API", "10", 1, name="Api"))

        plan = fetch_and_plan_from_api(client=FakeClient())
        self.assertEqual(plan.snapshot_policy, "present_only")
        self.assertEqual(plan.stocks_to_zero, [])
