"""RELEASE 46.1 Stage C: narrow stock skip when product_missing_category + stock_without_product."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.products.models import Category, Product
from apps.stores.models import Stock
from integrations.onec.importer import (
    ImportMode,
    ProductAction,
    SnapshotPolicy,
    StockAction,
    _collect_apply_blockers,
    _narrow_stock_skip_missing_category,
    _stores_by_confirmed_warehouse_id,
    plan_catalog_import_from_xml_strings,
)
from tests.onec_plan_apply_helpers import persist_and_apply_for_tests
from integrations.onec.reporting import (
    build_issue_counts,
    classify_issue,
    issue_for_log,
    partition_issues,
)
from tests.onec_test_utils import (
    TEST_OTHER_WH_ID,
    TEST_RETAIL_WH_ID,
    TEST_RETAIL_WH_NAME,
    ensure_confirmed_stores,
)

# В выгрузке есть другие папки, но нет 00-00010097 (кейс «Акционный товар»).
FOLDERS_OK = (
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
    parent: str = "F1",
    sklad: str = TEST_RETAIL_WH_NAME,
    sklad_id: str = TEST_RETAIL_WH_ID,
    series: str = "",
    series_id: str = "",
) -> str:
    extra = ""
    if series or series_id:
        extra = f' series="{series}" seriesID="{series_id}"'
    return (
        f'<Товар code="{code}" parentCode="{parent}" name="{name}" '
        f'price="{price}" quantity="{qty}" sklad="{sklad}" skladID="{sklad_id}"'
        f"{extra}/>"
    )


class MissingCategoryStockSkipTests(TestCase):
    def setUp(self):
        self.stores = ensure_confirmed_stores()
        # Папка F1 есть в БД, но для missing-category кейсов XML folders пустой / без parent
        self.cat = Category.objects.create(title="C", slug="mc-c", onec_code="F1")

    def test_same_code_missing_category_skips_stock_not_blocker(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(
                _row(
                    "00-00030516",
                    "100",
                    2,
                    name="Акционный товар",
                    parent="00-00010097",
                )
            ),
            mode=ImportMode.DRY_RUN,
        )
        types = [i["type"] for i in plan.issues]
        self.assertIn("product_missing_category", types)
        self.assertIn("stock_skipped_missing_category", types)
        self.assertNotIn("stock_without_product", types)

        skipped = [i for i in plan.issues if i["type"] == "stock_skipped_missing_category"]
        self.assertEqual(len(skipped), 1)
        self.assertFalse(skipped[0].get("severity"))
        self.assertEqual(skipped[0].get("onec_code"), "00-00030516")
        self.assertEqual(classify_issue(skipped[0]), "warning")

        self.assertEqual(plan.summary.get("skipped_stocks_missing_category"), 1)
        self.assertTrue(
            all(b.get("type") != "stock_without_product" for b in plan.apply_blockers)
        )
        self.assertTrue(
            all(b.get("type") != "stock_skipped_missing_category" for b in plan.apply_blockers)
        )
        stock_skips = [s for s in plan.stocks if s.onec_code == "00-00030516"]
        self.assertTrue(stock_skips)
        self.assertTrue(all(s.action == "skip" for s in stock_skips))

    def test_different_codes_other_remains_blocker(self):
        # Товар A: missing category → skip warning
        # Товар B: parent F1 есть в folders, но ambiguous/без create — обычный blocker
        # Для B: создаём sku-conflict ambiguous без категории? Проще: B без папки? Нет —
        # B с валидной папкой F1, но existing sku conflict → ambiguous → stock_without_product.
        Product.objects.create(
            title="Conflict",
            slug="mc-conf",
            sku="N-OTHER",
            onec_code="OTHER-ONEC",
            price=Decimal("1"),
            category=self.cat,
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(
                _row(
                    "00-00030516",
                    "100",
                    1,
                    name="Акционный товар",
                    parent="00-00010097",
                ),
                _row("N-OTHER", "10", 1, name="Other", parent="F1"),
            ),
            mode=ImportMode.DRY_RUN,
        )
        # A skipped narrowly (folders OK but parent 00-00010097 missing from XML folders)
        self.assertTrue(
            any(
                i["type"] == "stock_skipped_missing_category"
                and i.get("onec_code") == "00-00030516"
                for i in plan.issues
            )
        )
        # B stock_without_product remains blocker
        self.assertTrue(
            any(
                i["type"] == "stock_without_product" and i.get("onec_code") == "N-OTHER"
                for i in plan.issues
            )
        )
        self.assertFalse(plan.apply_allowed)
        self.assertTrue(
            any(
                b.get("type") == "stock_without_product" and b.get("onec_code") == "N-OTHER"
                for b in plan.apply_blockers
            )
        )

    def test_stock_without_product_alone_blocks(self):
        Product.objects.create(
            title="Conflict",
            slug="mc-alone",
            sku="N-ALONE",
            onec_code="DIFF",
            price=Decimal("1"),
            category=self.cat,
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(_row("N-ALONE", "10", 3, name="Alone", parent="F1")),
            mode=ImportMode.DRY_RUN,
        )
        self.assertTrue(
            any(i["type"] == "stock_without_product" for i in plan.issues)
        )
        self.assertFalse(
            any(i["type"] == "stock_skipped_missing_category" for i in plan.issues)
        )
        self.assertFalse(plan.apply_allowed)
        self.assertEqual(plan.summary.get("skipped_stocks_missing_category"), 0)

    def test_multi_warehouse_series_same_code(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(
                _row(
                    "00-00030516",
                    "100",
                    1,
                    name="Акционный товар",
                    parent="00-00010097",
                    series="S1",
                    series_id="ser-1",
                ),
                _row(
                    "00-00030516",
                    "100",
                    2,
                    name="Акционный товар",
                    parent="00-00010097",
                    series="S2",
                    series_id="ser-2",
                ),
                _row(
                    "00-00030516",
                    "100",
                    3,
                    name="Акционный товар",
                    parent="00-00010097",
                    sklad="Беслан",
                    sklad_id=TEST_OTHER_WH_ID,
                ),
            ),
            mode=ImportMode.DRY_RUN,
        )
        skipped = [
            i for i in plan.issues if i["type"] == "stock_skipped_missing_category"
        ]
        self.assertEqual(len(skipped), 3)
        self.assertEqual(plan.summary.get("skipped_stocks_missing_category"), 3)
        self.assertFalse(
            any(i["type"] == "stock_without_product" for i in plan.issues)
        )
        # Только missing-category warning — APPLY не блокируется этим типом
        # (могут быть другие blockers от unmapped confirmed warehouses — обычно нет)
        self.assertFalse(
            any(b.get("type") == "stock_without_product" for b in plan.apply_blockers)
        )

    def test_duplicate_issues_at_helper_before_blockers(self):
        """
        Дубли на входе helper (до _collect_apply_blockers):
        2× product_missing_category + 2× stock_without_product одного кода,
        1× stock_without_product другого кода.
        Счётчик = 2; чужой код остаётся blocker; notes без «папк» допустимы.
        """
        code_a = "00-00030516"
        code_b = "N-OTHER-BLOCK"
        issues = [
            {
                "type": "product_missing_category",
                "onec_code": code_a,
                "parent_code": "00-00010097",
                "name": "Акционный товар",
            },
            {
                "type": "product_missing_category",
                "onec_code": code_a,
                "parent_code": "00-00010097",
                "name": "Акционный товар",
            },
            {
                "type": "stock_without_product",
                "severity": True,
                "onec_code": code_a,
                "sklad_id": TEST_RETAIL_WH_ID,
                "message": "Остаток без сопоставленной карточки",
            },
            {
                "type": "stock_without_product",
                "severity": True,
                "onec_code": code_a,
                "sklad_id": TEST_OTHER_WH_ID,
                "message": "Остаток без сопоставленной карточки",
            },
            {
                "type": "stock_without_product",
                "severity": True,
                "onec_code": code_b,
                "sklad_id": TEST_RETAIL_WH_ID,
                "message": "Остаток без сопоставленной карточки",
            },
        ]
        # notes намеренно без «папк» — eligibility не должна зависеть от текста.
        product_actions = [
            ProductAction(
                onec_code=code_a,
                name="Акционный товар",
                parent_code="00-00010097",
                price="100",
                action="skip",
                notes="SKIP_REASON_STRUCTURED_ONLY",
            ),
            ProductAction(
                onec_code=code_b,
                name="Other",
                parent_code="F1",
                price="10",
                action="ambiguous",
                notes="sku conflict",
            ),
        ]
        stock_actions = [
            StockAction(
                onec_code=code_a,
                sklad="A",
                sklad_id=TEST_RETAIL_WH_ID,
                quantity="1",
                quantity_status="positive",
                action="skip",
                notes="Нет Product для остатка — строка в снимке не учитывается",
            ),
            StockAction(
                onec_code=code_a,
                sklad="B",
                sklad_id=TEST_OTHER_WH_ID,
                quantity="2",
                quantity_status="positive",
                action="skip",
                notes="Нет Product для остатка — строка в снимке не учитывается",
            ),
            StockAction(
                onec_code=code_b,
                sklad="A",
                sklad_id=TEST_RETAIL_WH_ID,
                quantity="3",
                quantity_status="positive",
                action="skip",
                notes="Нет Product для остатка — строка в снимке не учитывается",
            ),
        ]

        converted = _narrow_stock_skip_missing_category(
            issues=issues,
            stock_actions=stock_actions,
            product_actions=product_actions,
        )
        self.assertEqual(converted, 2)
        skipped = [i for i in issues if i["type"] == "stock_skipped_missing_category"]
        remaining_blockers = [
            i for i in issues if i["type"] == "stock_without_product"
        ]
        self.assertEqual(len(skipped), 2)
        self.assertTrue(all(i.get("onec_code") == code_a for i in skipped))
        self.assertTrue(all(not i.get("severity") for i in skipped))
        self.assertEqual(len(remaining_blockers), 1)
        self.assertEqual(remaining_blockers[0].get("onec_code"), code_b)
        self.assertTrue(remaining_blockers[0].get("severity"))
        # Дубли product_missing_category не увеличивают converted сверх числа stock-issues.
        self.assertEqual(
            sum(1 for i in issues if i["type"] == "product_missing_category"), 2
        )

        store_by_wid = _stores_by_confirmed_warehouse_id()
        blockers = _collect_apply_blockers(
            issues=issues, warehouses=[], store_by_wid=store_by_wid
        )
        self.assertTrue(
            any(
                b.get("type") == "stock_without_product" and b.get("onec_code") == code_b
                for b in blockers
            )
        )
        self.assertFalse(
            any(b.get("type") == "stock_skipped_missing_category" for b in blockers)
        )
        self.assertFalse(
            any(
                b.get("type") == "stock_without_product" and b.get("onec_code") == code_a
                for b in blockers
            )
        )

    def test_mixed_plan_one_skip_one_blocks_all(self):
        Product.objects.create(
            title="Conflict",
            slug="mc-mix",
            sku="N-MIX",
            onec_code="Y",
            price=Decimal("1"),
            category=self.cat,
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(
                _row(
                    "00-00030516",
                    "50",
                    1,
                    name="Акционный товар",
                    parent="00-00010097",
                ),
                _row("N-MIX", "10", 5, name="Mix", parent="F1"),
            ),
            mode=ImportMode.APPLY,
        )
        self.assertTrue(
            any(
                i["type"] == "stock_skipped_missing_category"
                and i["onec_code"] == "00-00030516"
                for i in plan.issues
            )
        )
        self.assertTrue(
            any(
                i["type"] == "stock_without_product" and i["onec_code"] == "N-MIX"
                for i in plan.issues
            )
        )
        self.assertFalse(plan.apply_allowed)
        before_products = Product.objects.count()
        before_stocks = Stock.objects.count()
        with self.assertRaises(ValueError):
            persist_and_apply_for_tests(plan)
        self.assertEqual(Product.objects.count(), before_products)
        self.assertEqual(Stock.objects.count(), before_stocks)

    def test_present_only_unchanged_for_missing_rows(self):
        product = Product.objects.create(
            title="Keep",
            slug="mc-keep",
            onec_code="N-KEEP",
            price=Decimal("10"),
            category=self.cat,
        )
        stock = Stock.objects.create(
            product=product,
            store=self.stores[TEST_RETAIL_WH_ID],
            quantity=9,
            reserved_quantity=2,
        )
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(
                _row(
                    "00-00030516",
                    "100",
                    1,
                    name="Акционный товар",
                    parent="00-00010097",
                )
            ),
            mode=ImportMode.APPLY,
            snapshot_policy=SnapshotPolicy.PRESENT_ONLY.value,
        )
        self.assertEqual(plan.snapshot_policy, "present_only")
        self.assertEqual(plan.stocks_to_zero, [])
        if plan.apply_allowed:
            persist_and_apply_for_tests(plan)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, 9)
        self.assertEqual(stock.reserved_quantity, 2)

    def test_full_snapshot_zero_policy_unchanged(self):
        product = Product.objects.create(
            title="Keep",
            slug="mc-fs",
            onec_code="N-FS",
            price=Decimal("10"),
            category=self.cat,
        )
        stock = Stock.objects.create(
            product=product,
            store=self.stores[TEST_RETAIL_WH_ID],
            quantity=4,
            reserved_quantity=1,
        )
        # XML без N-FS, только missing-category promo — full_snapshot должен zero N-FS
        # если apply_allowed. Missing-category skip не должен сам по себе блокировать.
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(
                _row(
                    "00-00030516",
                    "100",
                    1,
                    name="Акционный товар",
                    parent="00-00010097",
                )
            ),
            mode=ImportMode.APPLY,
            snapshot_policy=SnapshotPolicy.FULL_SNAPSHOT.value,
        )
        self.assertEqual(plan.snapshot_policy, "full_snapshot")
        self.assertFalse(
            any(i["type"] == "stock_without_product" for i in plan.issues)
        )
        if plan.apply_allowed:
            self.assertTrue(any(z.action == "zero" for z in plan.stocks_to_zero))
            persist_and_apply_for_tests(plan)
            stock.refresh_from_db()
            self.assertEqual(stock.quantity, 0)
            self.assertEqual(stock.reserved_quantity, 1)
        else:
            # Если есть сторонние blockers — zero-фаза не планируется; это тоже ок для B.
            self.assertEqual(plan.stocks_to_zero, [])

    def test_other_blockers_preserved(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(
                _row(
                    "00-00030516",
                    "100",
                    1,
                    name="Акционный товар",
                    parent="00-00010097",
                    sklad="X",
                    sklad_id="00000000-0000-0000-0000-000000000099",
                )
            ),
        )
        # unknown warehouse остаётся severity blocker; missing-category skip не срабатывает
        # на этой строке, потому что stock_without_product не создаётся (unknown_warehouse earlier).
        self.assertTrue(
            any(i["type"] == "unknown_warehouse" for i in plan.issues)
        )
        self.assertFalse(plan.apply_allowed)
        self.assertTrue(
            any(b.get("type") == "unknown_warehouse" for b in plan.apply_blockers)
        )

    def test_issue_counts_and_serialization(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_OK,
            _xml(
                _row(
                    "00-00030516",
                    "100",
                    1,
                    name="Акционный товар",
                    parent="00-00010097",
                )
            ),
        )
        partitioned = partition_issues(plan.issues)
        counts = build_issue_counts(partitioned)
        self.assertGreaterEqual(counts["warnings_count"], 1)
        skipped = [
            i for i in plan.issues if i["type"] == "stock_skipped_missing_category"
        ]
        self.assertEqual(len(skipped), 1)
        self.assertIn(skipped[0], partitioned["warning"])
        logged = issue_for_log(skipped[0])
        self.assertEqual(logged["type"], "stock_skipped_missing_category")
        self.assertEqual(logged["class"], "warning")
        self.assertEqual(logged["onec_code"], "00-00030516")
        self.assertEqual(plan.summary.get("skipped_stocks_missing_category"), 1)
        self.assertEqual(
            plan.summary.get("missing_category_products"),
            sum(1 for i in plan.issues if i["type"] == "product_missing_category"),
        )

    def test_stock_without_product_global_severity_unchanged(self):
        """Глобально stock_without_product остаётся blocker (не в WARNING_ISSUE_TYPES)."""
        from integrations.onec.reporting import WARNING_ISSUE_TYPES

        self.assertNotIn("stock_without_product", WARNING_ISSUE_TYPES)
        issue = {
            "type": "stock_without_product",
            "severity": True,
            "onec_code": "N1",
            "message": "x",
        }
        self.assertEqual(classify_issue(issue), "blocker")
