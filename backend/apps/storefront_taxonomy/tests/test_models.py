"""
S1.1: тесты моделей витринной таксономии.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.products.models import Category, Product
from apps.storefront_taxonomy.models import (
    ClassificationEvent,
    ClassificationRule,
    ClassificationRun,
    ProductClassificationOverride,
    ProductStorefrontAssignment,
    StorefrontCategory,
    UnmatchedProductQueue,
)
from apps.users.models import CustomUser


class StorefrontTaxonomyModelsTests(TestCase):
    def setUp(self):
        self.legacy_category = Category.objects.create(
            title="1С Категория",
            slug="onec-legacy-cat",
        )
        self.product = Product.objects.create(
            title="Тестовый телефон",
            slug="test-phone-sf",
            price=Decimal("1000.00"),
            category=self.legacy_category,
            is_active=True,
        )
        self.product_b = Product.objects.create(
            title="Тестовый аксессуар",
            slug="test-acc-sf",
            price=Decimal("100.00"),
            category=self.legacy_category,
            is_active=True,
        )
        self.user = CustomUser.objects.create_user(
            phone="79991112233",
            password="pw12345678",
            email="sf-tax@test.local",
        )

    def test_create_storefront_category(self):
        parent = StorefrontCategory.objects.create(
            title="Смартфоны",
            slug="smartfony",
            section_type=StorefrontCategory.SECTION_PRIMARY,
            sort_order=10,
        )
        child = StorefrontCategory.objects.create(
            title="Android",
            slug="android",
            parent=parent,
            section_type=StorefrontCategory.SECTION_PRIMARY,
            description="Android-смартфоны",
            meta_title="Android SEO",
            meta_description="SEO desc",
        )
        self.assertIsNotNone(child.id)
        self.assertEqual(child.parent_id, parent.id)
        self.assertTrue(child.is_active)
        self.assertEqual(parent.children.count(), 1)

    def test_duplicate_slug_rejected(self):
        StorefrontCategory.objects.create(title="A", slug="dup-slug")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StorefrontCategory.objects.create(title="B", slug="dup-slug")

    def test_create_classification_rule(self):
        cat = StorefrontCategory.objects.create(title="Наушники", slug="naushniki")
        rule = ClassificationRule.objects.create(
            code="headphones-title",
            title="Наушники по названию",
            description="title contains",
            priority=10,
            storefront_category=cat,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["наушник", "earbuds"]},
            schema_version=1,
        )
        self.assertEqual(rule.storefront_category_id, cat.id)
        self.assertTrue(rule.is_active)

    def test_rule_rejects_product_uuid_top_level(self):
        cat = StorefrontCategory.objects.create(title="X", slug="rule-x-top")
        with self.assertRaises(ValidationError):
            ClassificationRule.objects.create(
                code="bad-product-ref-top",
                title="Bad top",
                storefront_category=cat,
                condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
                condition_payload={"product_id": str(self.product.id)},
            )

    def test_rule_rejects_product_uuid_nested_dict(self):
        cat = StorefrontCategory.objects.create(title="X", slug="rule-x-nested")
        with self.assertRaises(ValidationError):
            ClassificationRule.objects.create(
                code="bad-product-ref-nested",
                title="Bad nested",
                storefront_category=cat,
                condition_type=ClassificationRule.CONDITION_COMPOSITE,
                condition_payload={
                    "all": [
                        {"title_contains": "наушник"},
                        {"product_uuid": str(self.product.id)},
                    ]
                },
            )

    def test_rule_rejects_product_uuid_inside_array(self):
        cat = StorefrontCategory.objects.create(title="X", slug="rule-x-array")
        with self.assertRaises(ValidationError):
            ClassificationRule.objects.create(
                code="bad-product-ref-array",
                title="Bad array",
                storefront_category=cat,
                condition_type=ClassificationRule.CONDITION_COMPOSITE,
                condition_payload={
                    "all": [
                        {"product_ids": [str(self.product.id)]},
                    ]
                },
            )

    def test_rule_accepts_valid_nested_payload(self):
        cat = StorefrontCategory.objects.create(title="X", slug="rule-x-ok")
        rule = ClassificationRule.objects.create(
            code="ok-nested-payload",
            title="OK nested",
            storefront_category=cat,
            condition_type=ClassificationRule.CONDITION_COMPOSITE,
            condition_payload={
                "all": [
                    {"title_contains": ["наушник", "earbuds"]},
                    {"brand_equals": "Apple"},
                    {"onec_category_slug": {"in": ["aksessuary", "naushniki"]}},
                ]
            },
        )
        self.assertEqual(rule.code, "ok-nested-payload")
        self.assertIn("all", rule.condition_payload)

    def test_single_assignment_per_product(self):
        cat = StorefrontCategory.objects.create(title="Phones", slug="phones-asg")
        ProductStorefrontAssignment.objects.create(
            product=self.product,
            storefront_category=cat,
            source=ProductStorefrontAssignment.SOURCE_RULE,
            confidence=Decimal("0.9500"),
            fingerprint="abc",
            classified_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductStorefrontAssignment.objects.create(
                    product=self.product,
                    storefront_category=cat,
                    source=ProductStorefrontAssignment.SOURCE_MANUAL,
                )

    def test_single_override_per_product(self):
        cat = StorefrontCategory.objects.create(title="Phones", slug="phones-ovr")
        ProductClassificationOverride.objects.create(
            product=self.product,
            storefront_category=cat,
            is_locked=True,
            reason="manual QA",
            created_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductClassificationOverride.objects.create(
                    product=self.product,
                    storefront_category=cat,
                    is_locked=False,
                )

    def test_override_independent_from_rule_assignment(self):
        cat_rule = StorefrontCategory.objects.create(title="Auto", slug="auto-cat")
        cat_manual = StorefrontCategory.objects.create(title="Manual", slug="manual-cat")
        rule = ClassificationRule.objects.create(
            code="auto-rule",
            title="Auto",
            storefront_category=cat_rule,
            condition_type=ClassificationRule.CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["телефон"]},
        )
        assignment = ProductStorefrontAssignment.objects.create(
            product=self.product,
            storefront_category=cat_rule,
            source=ProductStorefrontAssignment.SOURCE_RULE,
            rule=rule,
        )
        override = ProductClassificationOverride.objects.create(
            product=self.product,
            storefront_category=cat_manual,
            is_locked=True,
            reason="override wins",
            created_by=self.user,
        )
        self.assertEqual(assignment.storefront_category_id, cat_rule.id)
        self.assertEqual(override.storefront_category_id, cat_manual.id)
        self.assertEqual(assignment.product_id, override.product_id)

    def test_unmatched_queue_create(self):
        item = UnmatchedProductQueue.objects.create(
            product=self.product,
            status=UnmatchedProductQueue.STATUS_OPEN,
            reason="no rule matched",
            attempts=1,
            last_attempt_at=timezone.now(),
        )
        self.assertEqual(item.product_id, self.product.id)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UnmatchedProductQueue.objects.create(
                    product=self.product,
                    status=UnmatchedProductQueue.STATUS_OPEN,
                )

    def test_product_relations(self):
        cat = StorefrontCategory.objects.create(title="Rel", slug="rel-cat")
        ProductStorefrontAssignment.objects.create(
            product=self.product,
            storefront_category=cat,
            source=ProductStorefrontAssignment.SOURCE_SYSTEM,
        )
        ProductClassificationOverride.objects.create(
            product=self.product_b,
            storefront_category=cat,
            created_by=None,
        )
        UnmatchedProductQueue.objects.create(product=self.product_b)
        self.assertEqual(self.product.storefront_assignment.storefront_category_id, cat.id)
        self.assertEqual(self.product_b.storefront_override.storefront_category_id, cat.id)
        self.assertEqual(self.product_b.storefront_unmatched.status, UnmatchedProductQueue.STATUS_OPEN)

    def test_nullable_fks(self):
        cat = StorefrontCategory.objects.create(title="N", slug="nullable-cat")
        run = ClassificationRun.objects.create(
            run_id="run-nullable-1",
            trigger=ClassificationRun.TRIGGER_MANUAL,
            status=ClassificationRun.STATUS_COMPLETED,
            stats={"matched": 0},
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        event = ClassificationEvent.objects.create(
            run=run,
            product=None,
            old_category=None,
            new_category=None,
            status=ClassificationEvent.STATUS_ERROR,
            message="product missing",
            snapshot={},
        )
        assignment = ProductStorefrontAssignment.objects.create(
            product=self.product,
            storefront_category=cat,
            source=ProductStorefrontAssignment.SOURCE_MANUAL,
            rule=None,
            confidence=None,
            fingerprint=None,
            classified_at=None,
        )
        self.assertIsNone(event.product_id)
        self.assertIsNone(event.old_category_id)
        self.assertIsNone(event.new_category_id)
        self.assertIsNone(assignment.rule_id)
        override = ProductClassificationOverride.objects.create(
            product=self.product_b,
            storefront_category=cat,
            created_by=None,
        )
        self.assertIsNone(override.created_by_id)

    def test_parent_set_null_preserves_child(self):
        parent = StorefrontCategory.objects.create(title="P", slug="parent-del")
        child = StorefrontCategory.objects.create(
            title="C",
            slug="child-keep",
            parent=parent,
        )
        parent.delete()
        child.refresh_from_db()
        self.assertIsNone(child.parent_id)

    def test_existing_product_and_category_untouched(self):
        """Создание витринных сущностей не меняет Product.category / Category."""
        legacy_id = self.legacy_category.id
        product_cat_id = self.product.category_id
        cat = StorefrontCategory.objects.create(title="SF", slug="sf-preserve")
        ProductStorefrontAssignment.objects.create(
            product=self.product,
            storefront_category=cat,
            source=ProductStorefrontAssignment.SOURCE_MANUAL,
        )
        self.product.refresh_from_db()
        self.legacy_category.refresh_from_db()
        self.assertEqual(self.product.category_id, product_cat_id)
        self.assertEqual(self.legacy_category.id, legacy_id)
        self.assertEqual(Category.objects.filter(id=legacy_id).count(), 1)
        self.assertEqual(Product.objects.filter(id=self.product.id).count(), 1)

    def test_assignment_rule_set_null_on_rule_delete(self):
        cat = StorefrontCategory.objects.create(title="R", slug="rule-del-cat")
        rule = ClassificationRule.objects.create(
            code="temp-rule",
            title="Temp",
            storefront_category=cat,
            condition_type=ClassificationRule.CONDITION_BRAND_EQUALS,
            condition_payload={"brand": "Apple"},
        )
        assignment = ProductStorefrontAssignment.objects.create(
            product=self.product,
            storefront_category=cat,
            source=ProductStorefrontAssignment.SOURCE_RULE,
            rule=rule,
        )
        rule.delete()
        assignment.refresh_from_db()
        self.assertIsNone(assignment.rule_id)
        self.assertEqual(assignment.storefront_category_id, cat.id)

    def test_event_preserves_history_when_product_deleted_set_null(self):
        cat = StorefrontCategory.objects.create(title="E", slug="event-cat")
        run = ClassificationRun.objects.create(
            run_id="run-hist-1",
            trigger=ClassificationRun.TRIGGER_POST_IMPORT,
            status=ClassificationRun.STATUS_RUNNING,
        )
        event = ClassificationEvent.objects.create(
            run=run,
            product=self.product_b,
            old_category=None,
            new_category=cat,
            status=ClassificationEvent.STATUS_ASSIGNED,
            message="ok",
            snapshot={"title": self.product_b.title},
        )
        # Product deletion: event.product SET_NULL — история сохраняется
        product_id = self.product_b.id
        self.product_b.delete()
        event.refresh_from_db()
        self.assertIsNone(event.product_id)
        self.assertEqual(event.new_category_id, cat.id)
        self.assertEqual(event.snapshot.get("title"), "Тестовый аксессуар")
        self.assertFalse(Product.objects.filter(id=product_id).exists())

    def test_classification_run_delete_protected_when_events_exist(self):
        run = ClassificationRun.objects.create(
            run_id="run-protect-1",
            trigger=ClassificationRun.TRIGGER_MANUAL,
            status=ClassificationRun.STATUS_COMPLETED,
        )
        event = ClassificationEvent.objects.create(
            run=run,
            product=self.product,
            status=ClassificationEvent.STATUS_ASSIGNED,
            message="keep history",
            snapshot={},
        )
        with self.assertRaises(ProtectedError):
            run.delete()
        self.assertTrue(ClassificationRun.objects.filter(id=run.id).exists())
        self.assertTrue(ClassificationEvent.objects.filter(id=event.id).exists())
