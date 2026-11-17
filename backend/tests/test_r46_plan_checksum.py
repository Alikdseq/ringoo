"""RELEASE 46.1 Stage D.1 / D.1.1: canonical CatalogImportPlan + SHA-256 checksum."""

from __future__ import annotations

import copy
import json
from decimal import Decimal

from django.test import SimpleTestCase

from integrations.onec.importer import (
    CatalogImportPlan,
    CategoryAction,
    ImportMode,
    ProductAction,
    SnapshotPolicy,
    StockAction,
)
from integrations.onec.plan_security import (
    CANONICAL_SCHEMA_VERSION,
    MODE_IN_CHECKSUM,
    PlanCanonicalizeError,
    _decimal_to_canon_str,
    _jsonable,
    canonicalize_catalog_plan,
    catalog_plan_checksum,
)

# Golden vector schema_version=2 (D.1.1): mode excluded; Decimal/None rules hardened;
# JSON tie-breaker sort. Previous D.1 golden (schema_version=1, mode included):
# c5527bd2bd9eee96739f0383cfd720586380cf5623b0a3580508f336b5ec7b54
GOLDEN_CHECKSUM = "9d561f557f473f9da0b3eb6c37d9e46f254b76bd186a1c9e331fcce8c7357ac9"


def _base_plan(**overrides) -> CatalogImportPlan:
    plan = CatalogImportPlan(
        mode=ImportMode.APPLY.value,
        generated_at="2020-01-01T00:00:00+00:00",
        source_folders_path="folders.xml",
        source_products_path="products.xml",
        run_id="volatile-run",
        snapshot_policy=SnapshotPolicy.PRESENT_ONLY.value,
        categories=[
            CategoryAction(
                onec_code="F1",
                name="Phones",
                parent_code="",
                action="create",
                site_slug="phones",
            )
        ],
        products=[
            ProductAction(
                onec_code="N1",
                name="Phone",
                parent_code="F1",
                price="10.50",
                action="create",
            )
        ],
        stocks=[
            StockAction(
                onec_code="N1",
                sklad="Retail",
                sklad_id="wh-1",
                quantity="3",
                quantity_status="positive",
                action="upsert",
                series="",
                series_id="",
            )
        ],
        stocks_to_zero=[],
        warehouses=[{"sklad": "Retail", "sklad_id": "wh-1", "row_count": 99}],
        issues=[],
        apply_blockers=[],
        summary={"junk": 1},
    )
    for key, value in overrides.items():
        setattr(plan, key, value)
    return plan


class CatalogPlanChecksumTests(SimpleTestCase):
    def test_same_plan_same_checksum(self):
        a = _base_plan()
        b = _base_plan()
        self.assertEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))
        self.assertEqual(len(catalog_plan_checksum(a)), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in catalog_plan_checksum(a)))

    def test_dict_key_order_irrelevant_in_json(self):
        plan = _base_plan()
        payload = canonicalize_catalog_plan(plan)
        reversed_keys = {k: payload[k] for k in reversed(list(payload.keys()))}
        raw_a = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        raw_b = json.dumps(
            reversed_keys, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        self.assertEqual(raw_a, raw_b)
        self.assertEqual(catalog_plan_checksum(plan), GOLDEN_CHECKSUM)

    def test_independent_stock_order_does_not_change_checksum(self):
        plan = _base_plan(
            stocks=[
                StockAction(
                    onec_code="N1",
                    sklad="A",
                    sklad_id="wh-a",
                    quantity="1",
                    quantity_status="positive",
                    action="upsert",
                ),
                StockAction(
                    onec_code="N1",
                    sklad="B",
                    sklad_id="wh-b",
                    quantity="2",
                    quantity_status="positive",
                    action="upsert",
                ),
            ]
        )
        plan_rev = _base_plan(
            stocks=[
                StockAction(
                    onec_code="N1",
                    sklad="B",
                    sklad_id="wh-b",
                    quantity="2",
                    quantity_status="positive",
                    action="upsert",
                ),
                StockAction(
                    onec_code="N1",
                    sklad="A",
                    sklad_id="wh-a",
                    quantity="1",
                    quantity_status="positive",
                    action="upsert",
                ),
            ]
        )
        self.assertEqual(catalog_plan_checksum(plan), catalog_plan_checksum(plan_rev))

    def test_same_sort_keys_different_data_order_stable(self):
        """Одинаковые primary sort keys, разные quantity — порядок исходного списка не влияет."""
        a = _base_plan(
            stocks=[
                StockAction(
                    onec_code="N1",
                    sklad="Retail",
                    sklad_id="wh-1",
                    quantity="1",
                    quantity_status="positive",
                    action="upsert",
                    series="",
                    series_id="",
                ),
                StockAction(
                    onec_code="N1",
                    sklad="Retail",
                    sklad_id="wh-1",
                    quantity="2",
                    quantity_status="positive",
                    action="upsert",
                    series="",
                    series_id="",
                ),
            ]
        )
        b = _base_plan(
            stocks=[
                StockAction(
                    onec_code="N1",
                    sklad="Retail",
                    sklad_id="wh-1",
                    quantity="2",
                    quantity_status="positive",
                    action="upsert",
                    series="",
                    series_id="",
                ),
                StockAction(
                    onec_code="N1",
                    sklad="Retail",
                    sklad_id="wh-1",
                    quantity="1",
                    quantity_status="positive",
                    action="upsert",
                    series="",
                    series_id="",
                ),
            ]
        )
        self.assertEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))
        qs = [s["quantity"] for s in canonicalize_catalog_plan(a)["stocks"]]
        self.assertEqual(qs, ["1", "2"])

    def test_price_change_changes_checksum(self):
        a = _base_plan()
        b = _base_plan(
            products=[
                ProductAction(
                    onec_code="N1",
                    name="Phone",
                    parent_code="F1",
                    price="11.50",
                    action="create",
                )
            ]
        )
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_quantity_change_changes_checksum(self):
        a = _base_plan()
        b = _base_plan(
            stocks=[
                StockAction(
                    onec_code="N1",
                    sklad="Retail",
                    sklad_id="wh-1",
                    quantity="9",
                    quantity_status="positive",
                    action="upsert",
                )
            ]
        )
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_snapshot_policy_change_changes_checksum(self):
        a = _base_plan()
        b = _base_plan(snapshot_policy=SnapshotPolicy.FULL_SNAPSHOT.value)
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_stocks_to_zero_changes_checksum(self):
        a = _base_plan()
        b = _base_plan(
            snapshot_policy=SnapshotPolicy.FULL_SNAPSHOT.value,
            stocks_to_zero=[
                StockAction(
                    onec_code="N2",
                    sklad="Retail",
                    sklad_id="wh-1",
                    quantity="0",
                    quantity_status="zeroed",
                    action="zero",
                    site_product_id="p1",
                    site_store_id="s1",
                )
            ],
        )
        c = _base_plan(snapshot_policy=SnapshotPolicy.FULL_SNAPSHOT.value)
        self.assertNotEqual(catalog_plan_checksum(c), catalog_plan_checksum(b))
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_warehouse_change_changes_checksum(self):
        a = _base_plan()
        b = _base_plan(warehouses=[{"sklad": "Other", "sklad_id": "wh-2"}])
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_series_id_change_changes_checksum(self):
        a = _base_plan()
        b = _base_plan(
            stocks=[
                StockAction(
                    onec_code="N1",
                    sklad="Retail",
                    sklad_id="wh-1",
                    quantity="3",
                    quantity_status="positive",
                    action="upsert",
                    series="S",
                    series_id="ser-1",
                )
            ]
        )
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_action_change_changes_checksum(self):
        a = _base_plan()
        b = _base_plan(
            products=[
                ProductAction(
                    onec_code="N1",
                    name="Phone",
                    parent_code="F1",
                    price="10.50",
                    action="update",
                    site_id="pid-1",
                )
            ]
        )
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_blocker_and_issue_change_checksum(self):
        a = _base_plan()
        b = _base_plan(
            apply_blockers=[
                {
                    "type": "stock_without_product",
                    "message": "x",
                    "onec_code": "N9",
                    "sklad_id": "wh-1",
                }
            ]
        )
        c = _base_plan(
            issues=[
                {
                    "type": "stock_without_product",
                    "severity": True,
                    "onec_code": "N9",
                    "sklad_id": "wh-1",
                    "message": "x",
                }
            ]
        )
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(c))

    def test_decimal_no_float_no_precision_loss(self):
        self.assertEqual(_decimal_to_canon_str(Decimal("10.50")), "10.5")
        self.assertEqual(_decimal_to_canon_str(Decimal("10.5")), "10.5")
        self.assertEqual(
            _decimal_to_canon_str(Decimal("0.1") + Decimal("0.2")), "0.3"
        )
        self.assertEqual(_decimal_to_canon_str(Decimal("-0.0")), "0")
        self.assertEqual(_jsonable(Decimal("10.50")), "10.5")
        with self.assertRaises(PlanCanonicalizeError):
            _jsonable(0.1)

    def test_none_not_coerced_to_empty_or_zero(self):
        plan = _base_plan(
            products=[
                ProductAction(
                    onec_code="N1",
                    name="Phone",
                    parent_code="F1",
                    price=None,
                    action="skip",
                    site_id=None,
                )
            ]
        )
        payload = canonicalize_catalog_plan(plan)
        prod = payload["products"][0]
        self.assertIsNone(prod["price"])
        self.assertIsNone(prod["site_id"])
        self.assertNotEqual(prod["price"], "")
        self.assertNotEqual(prod["price"], 0)

    def test_none_differs_from_empty_string_in_warehouse(self):
        a = _base_plan(warehouses=[{"sklad": None, "sklad_id": "wh-1"}])
        b = _base_plan(warehouses=[{"sklad": "", "sklad_id": "wh-1"}])
        self.assertNotEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))
        self.assertIsNone(canonicalize_catalog_plan(a)["warehouses"][0]["sklad"])
        self.assertEqual(canonicalize_catalog_plan(b)["warehouses"][0]["sklad"], "")

    def test_generated_at_and_run_id_excluded(self):
        a = _base_plan(generated_at="1999-01-01T00:00:00+00:00", run_id="aaa")
        b = _base_plan(generated_at="2099-12-31T23:59:59+00:00", run_id="bbb")
        self.assertEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))
        self.assertEqual(catalog_plan_checksum(a), GOLDEN_CHECKSUM)

    def test_summary_and_notes_excluded(self):
        a = _base_plan()
        b = _base_plan(summary={"completely": "different"})
        b.stocks[0].notes = "changed notes must not affect checksum"
        b.products[0].notes = "also ignored"
        b.stocks[0].quantity_status = "rejected"
        self.assertEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))

    def test_mode_excluded_dry_run_vs_apply(self):
        self.assertFalse(MODE_IN_CHECKSUM)
        dry = _base_plan(mode=ImportMode.DRY_RUN.value)
        apply = _base_plan(mode=ImportMode.APPLY.value)
        self.assertEqual(catalog_plan_checksum(dry), catalog_plan_checksum(apply))
        self.assertNotIn("mode", canonicalize_catalog_plan(dry))
        self.assertEqual(CANONICAL_SCHEMA_VERSION, 2)

    def test_unsupported_type_raises(self):
        with self.assertRaises(PlanCanonicalizeError):
            _jsonable(object())
        with self.assertRaises(PlanCanonicalizeError):
            catalog_plan_checksum("not-a-plan")  # type: ignore[arg-type]

    def test_invalid_issue_types_rejected(self):
        with self.assertRaises(PlanCanonicalizeError):
            catalog_plan_checksum(
                _base_plan(issues=[{"type": "x", "severity": "yes"}])
            )
        with self.assertRaises(PlanCanonicalizeError):
            catalog_plan_checksum(
                _base_plan(issues=[{"type": "x", "names": [object()]}])
            )
        with self.assertRaises(PlanCanonicalizeError):
            catalog_plan_checksum(_base_plan(issues=["not-a-dict"]))

    def test_empty_lists_deterministic(self):
        a = _base_plan(
            stocks=[], products=[], categories=[], warehouses=[], issues=[]
        )
        b = copy.deepcopy(a)
        self.assertEqual(catalog_plan_checksum(a), catalog_plan_checksum(b))
        payload = canonicalize_catalog_plan(a)
        for key in (
            "stocks",
            "products",
            "categories",
            "warehouses",
            "issues",
            "stocks_to_zero",
            "apply_blockers",
        ):
            self.assertEqual(payload[key], [])

    def test_golden_vector(self):
        plan = _base_plan()
        self.assertEqual(catalog_plan_checksum(plan), GOLDEN_CHECKSUM)

    def test_category_order_preserved_in_canonical(self):
        """Топологический порядок categories не пересортировывается."""
        plan = _base_plan(
            categories=[
                CategoryAction(
                    onec_code="F1", name="Root", parent_code="", action="create"
                ),
                CategoryAction(
                    onec_code="F2", name="Child", parent_code="F1", action="create"
                ),
            ]
        )
        rev = _base_plan(
            categories=[
                CategoryAction(
                    onec_code="F2", name="Child", parent_code="F1", action="create"
                ),
                CategoryAction(
                    onec_code="F1", name="Root", parent_code="", action="create"
                ),
            ]
        )
        self.assertNotEqual(catalog_plan_checksum(plan), catalog_plan_checksum(rev))
        self.assertEqual(
            [c["onec_code"] for c in canonicalize_catalog_plan(plan)["categories"]],
            ["F1", "F2"],
        )
