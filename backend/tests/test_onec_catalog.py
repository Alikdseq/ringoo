"""Тесты парсера и dry-run импорта 1С (без HTTP к 1С)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from django.test import TestCase

from apps.products.models import Category, Product
from integrations.onec.client import OneCClient, OneCClientError
from integrations.onec.importer import ImportMode, plan_catalog_import, write_import_report
from integrations.onec.parser import (
    OneCParseError,
    _root_from_source,
    parse_catalog_files,
    parse_folders_xml,
    parse_products_xml,
)

FIXTURES = Path(__file__).resolve().parents[1] / "integrations" / "onec" / "fixtures"
FOLDERS = FIXTURES / "sample_folders.xml"
PRODUCTS = FIXTURES / "sample_products.xml"

_MINI_FOLDERS_XML = (
    '<?xml version="1.0"?>'
    "<ПапкиНоменклатуры>"
    '<Папка code="F1" parentCode="" name="Phones"/>'
    "</ПапкиНоменклатуры>"
)


class RootFromSourceTests(TestCase):
    """_root_from_source: XML string/bytes vs filesystem path (no Errno 36)."""

    def test_xml_string(self):
        root = _root_from_source(_MINI_FOLDERS_XML)
        self.assertTrue(root.tag.endswith("ПапкиНоменклатуры") or "Папки" in root.tag)

    def test_xml_bytes(self):
        root = _root_from_source(_MINI_FOLDERS_XML.encode("utf-8"))
        self.assertIsNotNone(root)

    def test_xml_path_object(self):
        root = _root_from_source(FOLDERS)
        self.assertIsNotNone(root)

    def test_xml_string_path_to_existing_file(self):
        root = _root_from_source(str(FOLDERS))
        self.assertIsNotNone(root)

    def test_empty_string(self):
        with self.assertRaises(OneCParseError) as ctx:
            _root_from_source("   ")
        self.assertIn("Пустой", str(ctx.exception))

    def test_empty_bytes(self):
        with self.assertRaises(OneCParseError) as ctx:
            _root_from_source(b"  \n")
        self.assertIn("Пустой", str(ctx.exception))

    def test_invalid_xml_string(self):
        with self.assertRaises(OneCParseError) as ctx:
            _root_from_source("<root><unclosed>")
        self.assertIn("Невалидный", str(ctx.exception))

    def test_bom_and_leading_whitespace(self):
        payload = "\ufeff  \n\t" + _MINI_FOLDERS_XML
        root = _root_from_source(payload)
        self.assertIsNotNone(root)

    def test_large_xml_string_not_treated_as_filename(self):
        # Longer than typical NAME_MAX (255); previously Path(source).is_file()
        # raised OSError Errno 36 on Linux.
        padding = "x" * 4000
        huge = (
            '<?xml version="1.0"?>'
            f'<ПапкиНоменклатуры><!--{padding}-->'
            '<Папка code="F1" parentCode="" name="Phones"/>'
            "</ПапкиНоменклатуры>"
        )
        self.assertGreater(len(huge), 255)
        root = _root_from_source(huge)
        self.assertIsNotNone(root)

    def test_xxe_rejected(self):
        evil = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            "<ПапкиНоменклатуры><Папка code='1' parentCode='' name='&xxe;'/></ПапкиНоменклатуры>"
        )
        with self.assertRaises(OneCParseError) as ctx:
            _root_from_source(evil)
        msg = str(ctx.exception).lower()
        self.assertTrue(
            "небезопас" in msg or "forbidden" in msg or "entity" in msg or " entit" in msg,
            msg,
        )

    def test_missing_file_path_string(self):
        with self.assertRaises(OneCParseError) as ctx:
            _root_from_source("/tmp/ringoo_missing_onec_catalog_xyz.xml")
        self.assertIn("не найден", str(ctx.exception).lower())


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

    def test_parse_folders_from_xml_string(self):
        folders = parse_folders_xml(_MINI_FOLDERS_XML)
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0].code, "F1")


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
