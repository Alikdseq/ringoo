"""S1.2.2: unit-тесты нормализации признаков."""

from django.test import SimpleTestCase

from apps.storefront_taxonomy.engine.normalizers import (
    NORMALIZER_VERSION,
    ProductFeatures,
    normalize_brand,
    normalize_features,
    normalize_slug,
    normalize_text,
)


class NormalizerTests(SimpleTestCase):
    def test_normalizer_version(self):
        self.assertEqual(NORMALIZER_VERSION, 1)

    def test_nfkc(self):
        # ﬁ (U+FB01) → fi
        self.assertEqual(normalize_text("ﬁPhone"), "fiphone")

    def test_casefold_latin_and_cyrillic(self):
        self.assertEqual(normalize_text("iPhone"), "iphone")
        self.assertEqual(normalize_text("НАУШНИКИ"), "наушники")
        self.assertEqual(normalize_text("Наушники"), "наушники")

    def test_whitespace_collapse_and_trim(self):
        self.assertEqual(normalize_text("  air   pods  "), "air pods")
        self.assertEqual(normalize_text("a\t\nb"), "a b")

    def test_none_and_empty(self):
        self.assertEqual(normalize_text(None), "")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_brand(None), "")
        self.assertEqual(normalize_brand(""), "")
        self.assertEqual(normalize_brand("   "), "")
        self.assertEqual(normalize_slug(None), "")
        self.assertEqual(normalize_slug(""), "")

    def test_slug_lower_trim_preserves_content(self):
        self.assertEqual(normalize_slug("  Aksessuary-Naushniki "), "aksessuary-naushniki")

    def test_idempotent(self):
        once = normalize_text("  Телефон  iPhone  ")
        self.assertEqual(normalize_text(once), once)
        brand = normalize_brand("  Apple ")
        self.assertEqual(normalize_brand(brand), brand)

    def test_normalize_features(self):
        raw = ProductFeatures(
            title="  AirPods  Pro ",
            brand="Apple",
            category_slug="Naushniki",
            category_onec_code=" 00-1 ",
            category_title_path=("Аксессуары", "Наушники"),
            category_slug_path=("Aksessuary", "Naushniki"),
        )
        norm = normalize_features(raw)
        self.assertEqual(norm.title, "airpods pro")
        self.assertEqual(norm.brand, "apple")
        self.assertEqual(norm.category_slug, "naushniki")
        self.assertEqual(norm.category_onec_code, "00-1")
        self.assertEqual(norm.category_title_path, ("аксессуары", "наушники"))
        self.assertEqual(norm.category_slug_path, ("aksessuary", "naushniki"))
        self.assertEqual(norm.normalizer_version, 1)
