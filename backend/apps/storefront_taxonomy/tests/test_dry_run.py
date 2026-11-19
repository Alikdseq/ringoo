"""S1.2.5: тесты Dry-run сервиса, отчёта и management command."""

from __future__ import annotations

import json
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection, reset_queries
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from io import StringIO

from apps.products.models import Category, Product
from apps.storefront_taxonomy.engine.resolution_types import ResolutionStatus
from apps.storefront_taxonomy.models import (
    ClassificationRule,
    ProductClassificationOverride,
    StorefrontCategory,
)
from apps.storefront_taxonomy.services.dry_run import (
    format_summary_text,
    run_storefront_dry_run,
)
from apps.storefront_taxonomy.services.report import (
    dump_dry_run_report,
    serialize_dry_run_report,
    validate_report_structure,
)


def _make_product(*, title: str, slug: str, category: Category, **kwargs) -> Product:
    defaults = dict(
        title=title,
        slug=slug,
        price=Decimal("100.00"),
        category=category,
        is_active=True,
    )
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


@override_settings(DEBUG=True)
class DryRunCoreTests(TestCase):
    def setUp(self):
        self.src = Category.objects.create(title="Телефоны", slug="src-phones")
        self.sf_phones = StorefrontCategory.objects.create(
            title="Phones", slug="sf-phones"
        )
        self.sf_empty = StorefrontCategory.objects.create(
            title="Empty", slug="sf-empty"
        )
        self.sf_acc = StorefrontCategory.objects.create(
            title="Accessories", slug="sf-acc"
        )
        self.rule_iphone = ClassificationRule.objects.create(
            code="iphone",
            title="iPhone rule",
            priority=10,
            storefront_category=self.sf_phones,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["iphone"]},
        )

    def test_empty_catalog(self):
        report = run_storefront_dry_run()
        validate_report_structure(report)
        self.assertEqual(report["summary"]["total_products"], 0)
        self.assertEqual(report["summary"]["processed_products"], 0)
        self.assertEqual(len(report["items"]), 0)
        self.assertEqual(len(report["categories"]), 3)
        empty = next(c for c in report["categories"] if c["slug"] == "sf-empty")
        self.assertEqual(empty["total_products"], 0)

    def test_single_match(self):
        _make_product(title="iPhone 15", slug="p-iphone", category=self.src)
        report = run_storefront_dry_run()
        self.assertEqual(report["summary"]["match"], 1)
        self.assertEqual(report["summary"]["assigned_total"], 1)
        item = report["items"][0]
        self.assertEqual(item["classification_status"], "match")
        self.assertEqual(item["storefront_category_slug"], "sf-phones")
        self.assertTrue(item["fingerprint"])

    def test_all_six_business_statuses_and_error(self):
        # MATCH — только rule_iphone
        _make_product(title="iPhone 15", slug="p-match", category=self.src)
        # UNMATCHED
        _make_product(title="Samsung Tablet", slug="p-unmatched", category=self.src)
        # CONFLICT — отдельные правила на уникальный токен
        ClassificationRule.objects.create(
            code="cf-a",
            title="Conflict A",
            priority=20,
            storefront_category=self.sf_phones,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["conflicttoken"]},
        )
        ClassificationRule.objects.create(
            code="cf-b",
            title="Conflict B",
            priority=20,
            storefront_category=self.sf_acc,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["conflicttoken"]},
        )
        _make_product(
            title="Device Conflicttoken X",
            slug="p-conflict",
            category=self.src,
        )
        # OVERRIDE locked
        p_ov = _make_product(title="Cable", slug="p-override", category=self.src)
        ProductClassificationOverride.objects.create(
            product=p_ov,
            storefront_category=self.sf_phones,
            is_locked=True,
        )
        # OVERRIDE_FALLBACK unlocked, no match
        p_fb = _make_product(title="Case", slug="p-fallback", category=self.src)
        ProductClassificationOverride.objects.create(
            product=p_fb,
            storefront_category=self.sf_acc,
            is_locked=False,
        )
        # NEEDS_REVIEW locked inactive target
        dead = StorefrontCategory.objects.create(
            title="Dead", slug="sf-dead", is_active=False
        )
        p_nr = _make_product(title="Watch", slug="p-needs", category=self.src)
        ProductClassificationOverride.objects.create(
            product=p_nr,
            storefront_category=dead,
            is_locked=True,
        )

        report = run_storefront_dry_run()
        by_status = {}
        for item in report["items"]:
            by_status.setdefault(item["classification_status"], []).append(item)

        self.assertIn("match", by_status)
        self.assertIn("unmatched", by_status)
        self.assertIn("conflict", by_status)
        self.assertIn("override", by_status)
        self.assertIn("override_fallback", by_status)
        self.assertIn("needs_review", by_status)

        s = report["summary"]
        self.assertEqual(
            s["processed_products"],
            s["match"]
            + s["override"]
            + s["override_fallback"]
            + s["conflict"]
            + s["unmatched"]
            + s["needs_review"]
            + s["error"],
        )
        self.assertEqual(
            s["assigned_total"],
            s["match"] + s["override"] + s["override_fallback"],
        )
        self.assertEqual(
            s["requires_attention"],
            s["conflict"] + s["unmatched"] + s["needs_review"] + s["error"],
        )

        problematic = {i["product_id"] for i in report["problematic_items"]}
        for item in report["items"]:
            if item["classification_status"] in {
                "conflict",
                "unmatched",
                "needs_review",
                "error",
            }:
                self.assertIn(item["product_id"], problematic)

    def test_technical_error_item(self):
        _make_product(title="iPhone 15", slug="p-ok", category=self.src)
        _make_product(title="iPhone SE", slug="p-bad", category=self.src)

        from apps.storefront_taxonomy.engine import classifier as clf_mod
        from apps.storefront_taxonomy.engine.normalizers import normalize_features as real_nf

        def selective(features):
            if features.title == "iPhone SE":
                raise TypeError("forced dry-run item error")
            return real_nf(features)

        with patch.object(clf_mod, "normalize_features", side_effect=selective):
            report = run_storefront_dry_run()

        self.assertGreaterEqual(report["summary"]["error"], 1)
        self.assertGreaterEqual(report["summary"]["match"], 1)
        err_items = [
            i for i in report["items"] if i["classification_status"] == "error"
        ]
        self.assertTrue(err_items)
        self.assertEqual(err_items[0]["technical_error_type"], "TypeError")
        self.assertIn(err_items[0]["product_id"], {
            i["product_id"] for i in report["problematic_items"]
        })

    def test_categories_distribution_and_empty(self):
        _make_product(title="iPhone 15", slug="p1", category=self.src, is_active=True)
        _make_product(
            title="iPhone inactive",
            slug="p2",
            category=self.src,
            is_active=False,
        )
        report = run_storefront_dry_run()
        phones = next(c for c in report["categories"] if c["slug"] == "sf-phones")
        empty = next(c for c in report["categories"] if c["slug"] == "sf-empty")
        self.assertEqual(phones["total_products"], 2)
        self.assertEqual(phones["active_products"], 1)
        self.assertEqual(phones["inactive_products"], 1)
        self.assertEqual(phones["match_count"], 2)
        self.assertEqual(empty["total_products"], 0)
        self.assertIn("percentage_of_catalog", phones)

    def test_inactive_rule_and_zero_match_rule(self):
        ClassificationRule.objects.create(
            code="inactive-r",
            title="Inactive",
            priority=1,
            is_active=False,
            storefront_category=self.sf_acc,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["iphone"]},
        )
        ClassificationRule.objects.create(
            code="never",
            title="Never",
            priority=50,
            storefront_category=self.sf_acc,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["zzzz-not-found"]},
        )
        _make_product(title="iPhone 15", slug="p1", category=self.src)
        report = run_storefront_dry_run()
        by_code = {r["code"]: r for r in report["rules"]}
        self.assertFalse(by_code["inactive-r"]["is_active"])
        self.assertEqual(by_code["inactive-r"]["matched_count"], 0)
        self.assertGreaterEqual(by_code["inactive-r"]["skipped_count"], 1)
        self.assertTrue(by_code["never"]["zero_match"])
        self.assertEqual(by_code["iphone"]["matched_count"], 1)

    def test_condition_errors_counted(self):
        ClassificationRule.objects.create(
            code="bad-regex",
            title="Bad",
            priority=5,
            storefront_category=self.sf_phones,
            condition_type=ClassificationRule.CONDITION_TITLE_REGEX,
            condition_payload={"pattern": "("},
        )
        _make_product(title="Something", slug="p1", category=self.src)
        report = run_storefront_dry_run()
        bad = next(r for r in report["rules"] if r["code"] == "bad-regex")
        self.assertGreaterEqual(bad["error_count"], 1)
        item = report["items"][0]
        self.assertTrue(item["rule_errors"])

    def test_summary_consistency_and_fingerprint(self):
        _make_product(title="iPhone 15", slug="p1", category=self.src)
        r1 = run_storefront_dry_run()
        r2 = run_storefront_dry_run()
        self.assertEqual(
            r1["fingerprints"]["ruleset_fingerprint"],
            r2["fingerprints"]["ruleset_fingerprint"],
        )
        self.assertEqual(
            [i["classification_status"] for i in r1["items"]],
            [i["classification_status"] for i in r2["items"]],
        )
        self.assertEqual(
            [i["fingerprint"] for i in r1["items"]],
            [i["fingerprint"] for i in r2["items"]],
        )

    def test_limit_reflected_in_metadata(self):
        for i in range(5):
            _make_product(
                title=f"iPhone {i}",
                slug=f"p-lim-{i}",
                category=self.src,
            )
        report = run_storefront_dry_run(limit=2)
        self.assertEqual(report["summary"]["total_products"], 2)
        self.assertTrue(report["metadata"]["limit_applied"])
        self.assertEqual(report["metadata"]["limit"], 2)
        self.assertTrue(
            any("limit=" in d for d in report["diagnostics"])
        )

    def test_json_serialization_and_file(self):
        _make_product(title="iPhone 15", slug="p1", category=self.src, sku="SKU-1")
        report = run_storefront_dry_run()
        text = serialize_dry_run_report(report, pretty=True)
        data = json.loads(text)
        self.assertIn("summary", data)
        self.assertEqual(data["metadata"]["mode"], "dry_run")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "report.json"
            saved = dump_dry_run_report(report, path, pretty=True)
            self.assertTrue(saved.exists())
            loaded = json.loads(saved.read_text(encoding="utf-8"))
            self.assertEqual(loaded["summary"]["match"], report["summary"]["match"])

    def test_no_write_queries(self):
        _make_product(title="iPhone 15", slug="p1", category=self.src)
        reset_queries()
        with CaptureQueriesContext(connection) as ctx:
            run_storefront_dry_run()
        writes = [
            q["sql"]
            for q in ctx.captured_queries
            if q["sql"].lstrip().upper().startswith(
                ("INSERT", "UPDATE", "DELETE")
            )
        ]
        self.assertEqual(writes, [])

    def test_no_n_plus_one(self):
        for i in range(8):
            _make_product(
                title=f"iPhone {i}",
                slug=f"p-n1-{i}",
                category=self.src,
            )
        with CaptureQueriesContext(connection) as ctx5:
            run_storefront_dry_run(limit=5)
        with CaptureQueriesContext(connection) as ctx8:
            run_storefront_dry_run(limit=8)
        # число SQL не растёт с N (только объём строк Product)
        self.assertEqual(len(ctx5.captured_queries), len(ctx8.captured_queries))
        self.assertLessEqual(len(ctx8.captured_queries), 10)

    def test_management_command_summary_and_output(self):
        _make_product(title="iPhone 15", slug="p-cmd", category=self.src)
        out = StringIO()
        call_command("storefront_dry_run", summary_only=True, stdout=out)
        text = out.getvalue()
        self.assertIn("Dry-run", text)
        self.assertIn("match:", text)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            out2 = StringIO()
            call_command(
                "storefront_dry_run",
                output=str(path),
                pretty=True,
                limit=1,
                stdout=out2,
            )
            self.assertTrue(path.exists())
            self.assertIn("Отчёт сохранён", out2.getvalue())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["metadata"]["limit"], 1)

    def test_format_summary_text(self):
        report = run_storefront_dry_run()
        text = format_summary_text(report)
        self.assertIn("processed_products", text)

    def test_conflict_not_counted_as_category_assignment(self):
        ClassificationRule.objects.create(
            code="iphone-b",
            title="B",
            priority=10,
            storefront_category=self.sf_acc,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["iphone"]},
        )
        _make_product(title="iPhone 15", slug="p-c", category=self.src)
        report = run_storefront_dry_run()
        self.assertEqual(report["summary"]["conflict"], 1)
        phones = next(c for c in report["categories"] if c["slug"] == "sf-phones")
        acc = next(c for c in report["categories"] if c["slug"] == "sf-acc")
        self.assertEqual(phones["total_products"], 0)
        self.assertEqual(acc["total_products"], 0)
