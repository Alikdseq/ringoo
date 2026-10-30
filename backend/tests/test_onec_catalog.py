"""Тесты парсера и dry-run импорта 1С (без HTTP к 1С)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from django.test import TestCase

from apps.products.models import Category, Product
from integrations.onec.client import OneCClient, OneCClientError
from integrations.onec.importer import ImportMode, plan_catalog_import, write_import_report
from integrations.onec.parser import parse_catalog_files, parse_folders_xml, parse_products_xml

FIXTURES = Path(__file__).resolve().parents[1] / "integrations" / "onec" / "fixtures"
FOLDERS = FIXTURES / "sample_folders.xml"
PRODUCTS = FIXTURES / "sample_products.xml"


class OneCParserTests(TestCase):
    def test_parse_folders(self):
        folders = parse_folders_xml(FOLDERS)
        self.assertGreaterEqual(len(folders), 1)
        self.assertIn("00-00000002", {f.code for f in folders})

    def test_parse_products_empty_quantity_is_none(self):
        rows = parse_products_xml(PRODUCTS)
        empty = [r for r in rows if not r.has_warehouse]
        self.assertTrue(empty)
        for r in empty:
            self.assertIsNone(r.parse_quantity())

    def test_parse_catalog_files(self):
        parsed = parse_catalog_files(FOLDERS, PRODUCTS)
        self.assertTrue(parsed.folders)
        self.assertTrue(parsed.product_rows)


class OneCDryRunTests(TestCase):
    def test_dry_run_does_not_write_db(self):
        before_c = Category.objects.count()
        before_p = Product.objects.count()
        plan = plan_catalog_import(FOLDERS, PRODUCTS, mode=ImportMode.DRY_RUN)
        self.assertEqual(plan.mode, "dry_run")
        self.assertGreater(plan.folder_count, 0)
        self.assertGreater(plan.unique_product_count, 0)
        self.assertEqual(Category.objects.count(), before_c)
        self.assertEqual(Product.objects.count(), before_p)

    def test_orphan_category_flagged(self):
        plan = plan_catalog_import(FOLDERS, PRODUCTS, mode=ImportMode.DRY_RUN)
        self.assertIn("product_missing_category", {i["type"] for i in plan.issues})

    def test_duplicate_codes_one_product_action(self):
        plan = plan_catalog_import(FOLDERS, PRODUCTS, mode=ImportMode.DRY_RUN)
        codes = [p.onec_code for p in plan.products]
        self.assertEqual(len(codes), len(set(codes)))

    def test_report_written(self):
        plan = plan_catalog_import(FOLDERS, PRODUCTS, mode=ImportMode.DRY_RUN)
        with tempfile.TemporaryDirectory() as tmp:
            out = write_import_report(plan, Path(tmp) / "report.json")
            self.assertTrue(out.is_file())
            self.assertIn("unique_product_count", out.read_text(encoding="utf-8"))


class OneCClientTests(TestCase):
    def test_disabled_by_default(self):
        client = OneCClient(enabled=False, base_url="http://localhost/razrab/hs")
        with self.assertRaises(OneCClientError):
            client.fetch_folders_xml()

    def test_build_url(self):
        client = OneCClient(enabled=False, base_url="http://localhost/razrab/hs")
        self.assertTrue(client.build_url("CatalogFolders/folders").endswith("CatalogFolders/folders"))


class OneCMatchExistingTests(TestCase):
    def test_match_existing_by_onec_code(self):
        root = Category.objects.create(
            title="IPhone 17",
            slug="iphone-17-onec-test",
            onec_code="00-00035237",
            is_active=True,
        )
        Product.objects.create(
            title="Existing iPhone",
            slug="existing-onec-iphone-17",
            sku="OLD-SKU",
            onec_code="00-00000126",
            category=root,
            price="100.00",
            is_active=True,
        )
        plan = plan_catalog_import(FOLDERS, PRODUCTS, mode=ImportMode.DRY_RUN)
        hit = next(p for p in plan.products if p.onec_code == "00-00000126")
        self.assertEqual(hit.action, "update")
        self.assertEqual(hit.matched_by, "onec_code")
        self.assertEqual(hit.site_slug, "existing-onec-iphone-17")
