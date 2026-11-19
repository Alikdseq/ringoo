"""
Тесты иерархии каталога 1С: главные разделы, дети, subtree-товары, без storefront_taxonomy.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.products.catalog_mains import MAIN_SECTION_SPECS
from apps.products.category_tree import iter_descendant_ids
from apps.products.management.commands.configure_catalog_mains import (
    Command as ConfigureMains,
)
from apps.products.models import Category, Product


class CatalogHierarchyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.root_phones = Category.objects.create(
            title="1.Сотовые телефоны/планшеты",
            slug="phones-root",
            onec_code="onec-root-phones",
            sort_order=1,
        )
        self.phones = Category.objects.create(
            title="1.1.Сотовые Телефоны",
            slug="sotovye-telefony",
            onec_code="onec-phones",
            parent=self.root_phones,
            sort_order=10,
        )
        self.apple = Category.objects.create(
            title="APPLE / IPhone",
            slug="apple-iphone",
            onec_code="onec-apple",
            parent=self.phones,
            sort_order=1,
        )
        self.iphone17 = Category.objects.create(
            title="IPhone 17",
            slug="iphone-17",
            onec_code="onec-ip17",
            parent=self.apple,
            sort_order=1,
        )
        self.tablets = Category.objects.create(
            title="1.2.Планшеты",
            slug="planshety-1c",
            onec_code="onec-tablets",
            parent=self.root_phones,
        )
        self.other = Category.objects.create(
            title="Случайная папка",
            slug="random-folder",
            onec_code="onec-random",
        )

        self.p_leaf = Product.objects.create(
            title="iPhone 17 Pro",
            slug="iphone-17-pro-test",
            price=Decimal("100000.00"),
            category=self.iphone17,
            is_active=True,
        )
        self.p_tablet = Product.objects.create(
            title="iPad Test",
            slug="ipad-test",
            price=Decimal("50000.00"),
            category=self.tablets,
            is_active=True,
        )

    def test_descendant_ids_follow_parent_links(self):
        ids = set(iter_descendant_ids(self.phones.id))
        self.assertIn(self.apple.id, ids)
        self.assertIn(self.iphone17.id, ids)
        self.assertNotIn(self.phones.id, ids)
        self.assertNotIn(self.tablets.id, ids)

    def test_cycle_safe(self):
        # искусственный цикл: apple → phones → apple
        self.apple.parent = self.phones
        self.apple.save()
        # phones.parent stays root; no cycle unless we set phones.parent=apple
        self.phones.parent = self.apple
        self.phones.save(update_fields=["parent"])
        ids = iter_descendant_ids(self.root_phones.id)
        # BFS stops on seen — no infinite loop
        self.assertIsInstance(ids, list)

    def test_configure_catalog_mains(self):
        ConfigureMains().handle(dry_run=False, clear_others=True, verbosity=0)
        self.phones.refresh_from_db()
        self.tablets.refresh_from_db()
        self.other.refresh_from_db()
        self.assertTrue(self.phones.is_catalog_main)
        self.assertTrue(self.tablets.is_catalog_main)
        self.assertFalse(self.other.is_catalog_main)
        self.assertEqual(self.phones.catalog_main_sort, 10)

    def test_api_main_sections_only(self):
        ConfigureMains().handle(dry_run=False, clear_others=True, verbosity=0)
        resp = self.client.get("/api/v1/products/categories/?main=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        slugs = {c["slug"] for c in data}
        self.assertIn("sotovye-telefony", slugs)
        self.assertIn("planshety-1c", slugs)
        self.assertNotIn("iphone-17", slugs)
        self.assertNotIn("apple-iphone", slugs)
        self.assertTrue(all(c["is_catalog_main"] for c in data))

    def test_api_children_of_parent(self):
        resp = self.client.get(
            f"/api/v1/products/categories/?parent={self.phones.id}"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["slug"], "apple-iphone")

    def test_api_retrieve_by_slug(self):
        resp = self.client.get("/api/v1/products/categories/iphone-17/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "IPhone 17")
        self.assertEqual(resp.json()["onec_code"], "onec-ip17")

    def test_products_include_subtree(self):
        resp = self.client.get(
            "/api/v1/products/products/?category=sotovye-telefony"
        )
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        slugs = {p["slug"] for p in results}
        self.assertIn("iphone-17-pro-test", slugs)
        self.assertNotIn("ipad-test", slugs)

    def test_product_category_unchanged_after_mains(self):
        before = self.p_leaf.category_id
        ConfigureMains().handle(dry_run=False, clear_others=True, verbosity=0)
        self.p_leaf.refresh_from_db()
        self.assertEqual(self.p_leaf.category_id, before)
        self.assertEqual(self.p_leaf.category.onec_code, "onec-ip17")

    def test_main_specs_do_not_invent_missing(self):
        missing = [s for s in MAIN_SECTION_SPECS if s.onec_title is None]
        self.assertGreaterEqual(len(missing), 2)
        labels = {s.desired_label for s in missing}
        self.assertIn("Услуги", labels)
        self.assertIn("Сопутствующие товары", labels)

    def test_categories_list_not_paginated_truncated(self):
        # создаём >20 категорий — API должен вернуть все
        for i in range(25):
            Category.objects.create(
                title=f"Extra {i}",
                slug=f"extra-{i}",
                onec_code=f"extra-{i}",
            )
        resp = self.client.get("/api/v1/products/categories/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 25)
