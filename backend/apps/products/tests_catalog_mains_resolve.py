from django.test import TestCase
from apps.products.catalog_mains import MainSectionSpec
from apps.products.management.commands.configure_catalog_mains import Command, _resolve_category
from apps.products.models import Category


class CatalogMainsResolveTests(TestCase):
    def test_ambiguous_title_skipped_slug_disambiguates(self):
        Category.objects.create(title="Очки", slug="ochki-a", onec_code="a1")
        Category.objects.create(title="Очки", slug="ochki-b", onec_code="a2")
        cat, status = _resolve_category(MainSectionSpec("Очки", "Очки", 200))
        self.assertEqual(status, "ambiguous")
        self.assertIsNone(cat)
        cat2, status2 = _resolve_category(
            MainSectionSpec("Очки", "Очки", 200, slug="ochki-a")
        )
        self.assertEqual(status2, "matched")
        self.assertEqual(cat2.slug, "ochki-a")

    def test_dry_run_writes_nothing(self):
        Category.objects.create(title="1.1.Сотовые Телефоны", slug="phones-x")
        before_flags = list(
            Category.objects.values_list("id", "is_catalog_main", "catalog_main_sort")
        )
        before_parents = list(Category.objects.values_list("id", "parent_id"))
        before_count = Category.objects.count()
        Command().handle(dry_run=True, clear_others=True, verbosity=0)
        self.assertEqual(Category.objects.count(), before_count)
        self.assertEqual(
            list(Category.objects.values_list("id", "is_catalog_main", "catalog_main_sort")),
            before_flags,
        )
        self.assertEqual(
            list(Category.objects.values_list("id", "parent_id")),
            before_parents,
        )

    def test_apply_only_flags(self):
        cat = Category.objects.create(
            title="1.1.Сотовые Телефоны",
            slug="phones-y",
            onec_code="onec-phones-y",
        )
        parent_id = cat.parent_id
        Command().handle(dry_run=False, clear_others=True, verbosity=0)
        cat.refresh_from_db()
        self.assertTrue(cat.is_catalog_main)
        self.assertEqual(cat.catalog_main_sort, 10)
        self.assertEqual(cat.parent_id, parent_id)
        self.assertEqual(cat.title, "1.1.Сотовые Телефоны")
