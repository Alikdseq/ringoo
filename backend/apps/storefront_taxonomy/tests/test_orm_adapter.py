"""S1.2.4.1: тесты ORM Adapter / DTO."""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase

from apps.products.models import Category, Product
from apps.storefront_taxonomy.adapters.orm import (
    AdapterError,
    build_category_paths,
    load_classification_bundle,
    load_overrides_for_products,
    load_rules,
    override_to_input,
    product_to_features,
    rule_to_input,
    storefront_category_to_ref,
)
from apps.storefront_taxonomy.models import (
    ClassificationRule,
    ProductClassificationOverride,
    StorefrontCategory,
)


class OrmAdapterProductFeaturesTests(TestCase):
    def setUp(self):
        self.root = Category.objects.create(title="Электроника", slug="electronics")
        self.child = Category.objects.create(
            title="Телефоны",
            slug="telefony",
            parent=self.root,
            onec_code="00-ph",
        )
        self.product = Product.objects.create(
            title="iPhone 15",
            slug="iphone-15-ad",
            price=Decimal("1000.00"),
            category=self.child,
            brand="Apple",
            is_active=True,
        )

    def test_product_to_features(self):
        feats = product_to_features(self.product)
        self.assertEqual(feats.title, "iPhone 15")
        self.assertEqual(feats.brand, "Apple")
        self.assertEqual(feats.category_slug, "telefony")
        self.assertEqual(feats.category_onec_code, "00-ph")
        self.assertEqual(feats.category_title_path, ("Электроника", "Телефоны"))
        self.assertEqual(feats.category_slug_path, ("electronics", "telefony"))
        self.assertFalse(hasattr(feats, "product_id"))

    def test_root_category_path(self):
        root_only = Category.objects.create(title="Root", slug="root-only", onec_code="r1")
        p = Product.objects.create(
            title="X",
            slug="x-root",
            price=Decimal("1"),
            category=root_only,
        )
        feats = product_to_features(p)
        self.assertEqual(feats.category_title_path, ("Root",))
        self.assertEqual(feats.category_slug_path, ("root-only",))

    def test_multi_level_path(self):
        grand = Category.objects.create(
            title="Смартфоны",
            slug="smartfony",
            parent=self.child,
            onec_code="00-sm",
        )
        p = Product.objects.create(
            title="Y",
            slug="y-deep",
            price=Decimal("1"),
            category=grand,
        )
        feats = product_to_features(p)
        self.assertEqual(
            feats.category_title_path,
            ("Электроника", "Телефоны", "Смартфоны"),
        )
        self.assertEqual(
            feats.category_slug_path,
            ("electronics", "telefony", "smartfony"),
        )

    def test_missing_category_raises(self):
        fake_id = uuid.uuid4()
        broken = SimpleNamespace(
            id=uuid.uuid4(),
            title="Broken",
            brand=None,
            category_id=fake_id,
            category=None,
        )
        with self.assertRaises(AdapterError):
            product_to_features(broken)  # type: ignore[arg-type]

    def test_missing_parent_in_map_raises(self):
        orphan_parent_id = uuid.uuid4()
        leaf = Category.objects.create(title="Leaf", slug="leaf-ad")
        # Simulate stale parent_id not in map
        leaf.parent_id = orphan_parent_id
        cat_map = {leaf.id: leaf}
        with self.assertRaises(AdapterError):
            build_category_paths(leaf, cat_map)

    def test_inactive_source_category_still_builds_path(self):
        inactive = Category.objects.create(
            title="Архив",
            slug="archive-ad",
            is_active=False,
            onec_code="00-arch",
        )
        p = Product.objects.create(
            title="Z",
            slug="z-inactive-cat",
            price=Decimal("1"),
            category=inactive,
        )
        feats = product_to_features(p)
        self.assertEqual(feats.category_slug, "archive-ad")
        self.assertEqual(feats.category_title_path, ("Архив",))
        self.assertFalse(inactive.is_active)


class OrmAdapterRulesTests(TestCase):
    def setUp(self):
        self.sf = StorefrontCategory.objects.create(title="Phones", slug="sf-phones")
        self.sf_inactive = StorefrontCategory.objects.create(
            title="Dead",
            slug="sf-dead",
            is_active=False,
        )

    def test_storefront_category_to_ref(self):
        ref = storefront_category_to_ref(self.sf)
        self.assertEqual(ref.id, str(self.sf.id))
        self.assertTrue(ref.is_active)
        self.assertEqual(ref.slug, "sf-phones")

        ref_i = storefront_category_to_ref(self.sf_inactive)
        self.assertFalse(ref_i.is_active)

    def test_active_and_inactive_rules(self):
        active = ClassificationRule.objects.create(
            code="active-r",
            title="A",
            priority=10,
            is_active=True,
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["iphone"]},
        )
        inactive = ClassificationRule.objects.create(
            code="inactive-r",
            title="B",
            priority=5,
            is_active=False,
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["case"]},
        )
        rules = load_rules(active_only=False)
        codes = [r.code for r in rules]
        # priority 5 (inactive) before priority 10 (active)
        self.assertEqual(codes, ["inactive-r", "active-r"])
        self.assertFalse(rules[0].is_active)
        self.assertTrue(rules[1].is_active)
        self.assertEqual(str(active.id), rules[1].id)

        only_active = load_rules(active_only=True)
        self.assertEqual([r.code for r in only_active], ["active-r"])
        self.assertEqual(str(active.id), only_active[0].id)

    def test_deterministic_rule_order(self):
        ClassificationRule.objects.create(
            code="b-rule",
            title="B",
            priority=10,
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["b"]},
        )
        ClassificationRule.objects.create(
            code="a-rule",
            title="A",
            priority=10,
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["a"]},
        )
        ClassificationRule.objects.create(
            code="c-rule",
            title="C",
            priority=1,
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["c"]},
        )
        r1 = [r.code for r in load_rules()]
        r2 = [r.code for r in load_rules()]
        self.assertEqual(r1, r2)
        self.assertEqual(r1, ["c-rule", "a-rule", "b-rule"])

    def test_invalid_payload_preserved_not_replaced(self):
        rule = ClassificationRule.objects.create(
            code="ok-then-corrupt",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["x"]},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload=["not", "a", "dict"]
        )
        rule.refresh_from_db()
        dto = rule_to_input(rule)
        self.assertEqual(dto.condition_payload, ["not", "a", "dict"])

    def test_forbidden_product_id_in_payload_raises(self):
        rule = ClassificationRule.objects.create(
            code="will-forbid",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["x"]},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload={"contains": ["x"], "product_id": str(uuid.uuid4())}
        )
        rule.refresh_from_db()
        with self.assertRaises(AdapterError) as ctx:
            rule_to_input(rule)
        self.assertIn("product_id", str(ctx.exception))

    def test_nested_forbidden_product_uuid_raises(self):
        rule = ClassificationRule.objects.create(
            code="nested-forbid",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_COMPOSITE,
            condition_payload={
                "op": "and",
                "args": [
                    {
                        "type": "title_contains",
                        "payload": {"contains": ["a"]},
                    }
                ],
            },
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload={
                "op": "and",
                "args": [
                    {
                        "type": "title_contains",
                        "payload": {"product_ids": ["1"]},
                    }
                ],
            }
        )
        rule.refresh_from_db()
        with self.assertRaises(AdapterError):
            rule_to_input(rule)

    def test_toplevel_list_with_product_id_raises(self):
        rule = ClassificationRule.objects.create(
            code="list-pid",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["x"]},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload=[{"product_id": "abc"}]
        )
        rule.refresh_from_db()
        with self.assertRaises(AdapterError) as ctx:
            rule_to_input(rule)
        self.assertIn("product_id", str(ctx.exception))

    def test_toplevel_list_with_product_uuid_raises(self):
        rule = ClassificationRule.objects.create(
            code="list-puuid",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["x"]},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload=[{"product_uuid": str(uuid.uuid4())}]
        )
        rule.refresh_from_db()
        with self.assertRaises(AdapterError) as ctx:
            rule_to_input(rule)
        self.assertIn("product_uuid", str(ctx.exception))

    def test_nested_dict_inside_list_forbidden(self):
        rule = ClassificationRule.objects.create(
            code="list-nested-dict",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["x"]},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload=[
                {"type": "title_contains", "payload": {"product_ids": ["1"]}}
            ]
        )
        rule.refresh_from_db()
        with self.assertRaises(AdapterError) as ctx:
            rule_to_input(rule)
        self.assertIn("product_ids", str(ctx.exception))

    def test_nested_list_inside_dict_forbidden(self):
        rule = ClassificationRule.objects.create(
            code="dict-nested-list",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_COMPOSITE,
            condition_payload={"op": "and", "args": []},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload={
                "op": "and",
                "args": [[{"product_uuids": ["u1"]}]],
            }
        )
        rule.refresh_from_db()
        with self.assertRaises(AdapterError) as ctx:
            rule_to_input(rule)
        self.assertIn("product_uuids", str(ctx.exception))

    def test_deep_nesting_forbidden_products_key(self):
        rule = ClassificationRule.objects.create(
            code="deep-nest",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_COMPOSITE,
            condition_payload={"op": "and", "args": []},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload={
                "op": "and",
                "args": [
                    {
                        "type": "composite",
                        "payload": {
                            "op": "or",
                            "args": [
                                {"type": "x", "payload": {"products": ["p1"]}},
                            ],
                        },
                    }
                ],
            }
        )
        rule.refresh_from_db()
        with self.assertRaises(AdapterError) as ctx:
            rule_to_input(rule)
        self.assertIn("products", str(ctx.exception))

    def test_safe_toplevel_list_without_forbidden_keys(self):
        rule = ClassificationRule.objects.create(
            code="safe-list",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["x"]},
        )
        safe = [{"contains": ["iphone"]}, {"contains": ["case"]}]
        ClassificationRule.objects.filter(pk=rule.pk).update(condition_payload=safe)
        rule.refresh_from_db()
        dto = rule_to_input(rule)
        self.assertIsInstance(dto.condition_payload, list)
        self.assertEqual(dto.condition_payload, safe)

    def test_nondict_payload_preserves_type_and_content(self):
        rule = ClassificationRule.objects.create(
            code="preserve-list",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["x"]},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload=["not", "a", "dict"]
        )
        rule.refresh_from_db()
        dto = rule_to_input(rule)
        self.assertEqual(dto.condition_payload, ["not", "a", "dict"])
        self.assertIsInstance(dto.condition_payload, list)

    def test_payload_copy_isolation(self):
        rule = ClassificationRule.objects.create(
            code="copy-iso",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["iphone"]},
        )
        dto = rule_to_input(rule)
        dto.condition_payload["contains"].append("mutated")
        rule.refresh_from_db()
        self.assertEqual(rule.condition_payload["contains"], ["iphone"])

    def test_list_payload_copy_isolation(self):
        rule = ClassificationRule.objects.create(
            code="copy-iso-list",
            title="T",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["iphone"]},
        )
        ClassificationRule.objects.filter(pk=rule.pk).update(
            condition_payload=[{"contains": ["iphone"]}]
        )
        rule.refresh_from_db()
        dto = rule_to_input(rule)
        dto.condition_payload[0]["contains"].append("mutated")
        rule.refresh_from_db()
        self.assertEqual(rule.condition_payload, [{"contains": ["iphone"]}])


class OrmAdapterOverrideTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(title="C", slug="c-ovr")
        self.product = Product.objects.create(
            title="P",
            slug="p-ovr",
            price=Decimal("10"),
            category=self.cat,
        )
        self.sf = StorefrontCategory.objects.create(title="SF", slug="sf-ovr")

    def test_locked_override(self):
        ov = ProductClassificationOverride.objects.create(
            product=self.product,
            storefront_category=self.sf,
            is_locked=True,
            reason="qa",
        )
        dto = override_to_input(ov)
        self.assertTrue(dto.is_locked)
        self.assertEqual(dto.category.id, str(self.sf.id))
        self.assertEqual(dto.reason, "qa")

    def test_unlocked_override(self):
        ov = ProductClassificationOverride.objects.create(
            product=self.product,
            storefront_category=self.sf,
            is_locked=False,
        )
        dto = override_to_input(ov)
        self.assertFalse(dto.is_locked)

    def test_missing_override(self):
        mapping = load_overrides_for_products([self.product.id])
        self.assertEqual(mapping, {})

    def test_override_loaded_in_map(self):
        ProductClassificationOverride.objects.create(
            product=self.product,
            storefront_category=self.sf,
            is_locked=True,
        )
        mapping = load_overrides_for_products([self.product.id])
        self.assertIn(str(self.product.id), mapping)
        self.assertTrue(mapping[str(self.product.id)].is_locked)


class OrmAdapterBatchQueryTests(TestCase):
    def setUp(self):
        self.root = Category.objects.create(title="R", slug="r-batch")
        self.sf = StorefrontCategory.objects.create(title="SF", slug="sf-batch")
        self.products = []
        for i in range(5):
            leaf = Category.objects.create(
                title=f"L{i}",
                slug=f"l-batch-{i}",
                parent=self.root,
            )
            p = Product.objects.create(
                title=f"P{i}",
                slug=f"p-batch-{i}",
                price=Decimal("1"),
                category=leaf,
            )
            self.products.append(p)
        ClassificationRule.objects.create(
            code="batch-rule",
            title="B",
            storefront_category=self.sf,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["p"]},
        )
        ProductClassificationOverride.objects.create(
            product=self.products[0],
            storefront_category=self.sf,
            is_locked=True,
        )

    def test_bundle_no_n_plus_one(self):
        ids = [p.id for p in self.products]
        # 1 Category all + 1 Product + 1 Rules + 1 Overrides = 4
        with self.assertNumQueries(4):
            bundle = load_classification_bundle(product_ids=ids, active_rules_only=False)
        self.assertEqual(len(bundle.features_by_product_id), 5)
        self.assertEqual(len(bundle.rules), 1)
        self.assertEqual(len(bundle.overrides_by_product_id), 1)
        # paths populated
        sample = next(iter(bundle.features_by_product_id.values()))
        self.assertTrue(len(sample.category_slug_path) >= 1)

    def test_bundle_does_not_mutate_orm(self):
        p = self.products[0]
        title_before = p.title
        bundle = load_classification_bundle(product_ids=[p.id])
        feats = bundle.features_by_product_id[str(p.id)]
        # frozen features — attempt would fail; ensure ORM unchanged
        p.refresh_from_db()
        self.assertEqual(p.title, title_before)
        self.assertEqual(feats.title, title_before)
