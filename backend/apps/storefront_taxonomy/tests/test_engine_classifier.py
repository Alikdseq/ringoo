"""S1.2.4.2: тесты Classification Service (Classifier)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection, reset_queries
from django.test import SimpleTestCase
from django.test.utils import override_settings

from apps.storefront_taxonomy.adapters.orm import ClassificationInputBundle
from apps.storefront_taxonomy.engine.classifier import (
    ClassifierError,
    ItemOutcome,
    classify_bundle,
)
from apps.storefront_taxonomy.engine import classifier as classifier_mod
from apps.storefront_taxonomy.engine import fingerprint as fingerprint_mod
from apps.storefront_taxonomy.engine import normalizers as normalizers_mod
from apps.storefront_taxonomy.engine.fingerprint import (
    FingerprintError,
    classification_fingerprint,
    combine_classification_fingerprint,
    features_fingerprint,
    ruleset_fingerprint,
)
from apps.storefront_taxonomy.engine.normalizers import ProductFeatures
from apps.storefront_taxonomy.engine.resolution_types import (
    CategoryRef,
    OverrideInput,
    ResolutionSource,
    ResolutionStatus,
    RuleInput,
)
from apps.storefront_taxonomy.engine.schemas import (
    CONDITION_TITLE_CONTAINS,
)


def _cat(cid: str, *, active: bool = True, slug: str = "") -> CategoryRef:
    return CategoryRef(id=cid, is_active=active, slug=slug or cid)


def _rule(
    *,
    rid: str,
    code: str,
    priority: int,
    contains: list[str],
    target: CategoryRef,
    active: bool = True,
) -> RuleInput:
    return RuleInput(
        id=rid,
        code=code,
        priority=priority,
        is_active=active,
        condition_type=CONDITION_TITLE_CONTAINS,
        condition_payload={"contains": contains},
        schema_version=1,
        target_category=target,
    )


def _features(
    *,
    title: str = "iPhone 15",
    brand: str | None = "Apple",
    slug: str = "telefony",
    onec: str | None = "00-ph",
    title_path: tuple[str, ...] = ("Электроника", "Телефоны"),
    slug_path: tuple[str, ...] = ("electronics", "telefony"),
) -> ProductFeatures:
    return ProductFeatures(
        title=title,
        brand=brand,
        category_slug=slug,
        category_onec_code=onec,
        category_title_path=title_path,
        category_slug_path=slug_path,
    )


def _bundle(
    features: dict[str, ProductFeatures],
    rules: tuple[RuleInput, ...],
    overrides: dict[str, OverrideInput] | None = None,
) -> ClassificationInputBundle:
    return ClassificationInputBundle(
        features_by_product_id=features,
        rules=rules,
        overrides_by_product_id=overrides or {},
    )


@override_settings(DEBUG=True)
class ClassifierMatchUnmatchedConflictTests(SimpleTestCase):
    def test_single_match(self):
        sf = _cat("sf-phones", slug="phones")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=sf,
            ),
        )
        bundle = _bundle({"p1": _features()}, rules)
        result = classify_bundle(bundle)
        item = result.by_product_id()["p1"]
        self.assertEqual(item.outcome, ItemOutcome.RESOLVED)
        assert item.resolution is not None
        self.assertEqual(item.resolution.status, ResolutionStatus.MATCH)
        self.assertEqual(item.resolution.category_id, "sf-phones")
        self.assertEqual(item.resolution.source, ResolutionSource.RULE)
        self.assertEqual(item.resolution.winning_rule_code, "iphone")
        self.assertEqual(item.resolution.winning_priority, 10)
        self.assertTrue(item.resolution.fingerprint)
        self.assertEqual(item.ruleset_fingerprint, result.ruleset_fingerprint)

    def test_unmatched(self):
        sf = _cat("sf-phones")
        rules = (
            _rule(
                rid="r1",
                code="case",
                priority=10,
                contains=["чехол"],
                target=sf,
            ),
        )
        result = classify_bundle(_bundle({"p1": _features()}, rules))
        res = result.by_product_id()["p1"].resolution
        assert res is not None
        self.assertEqual(res.status, ResolutionStatus.UNMATCHED)
        self.assertIsNone(res.category_id)
        self.assertIn("Нет совпавших", res.explanation)

    def test_conflict(self):
        a = _cat("sf-a")
        b = _cat("sf-b")
        rules = (
            _rule(rid="r1", code="a", priority=5, contains=["iphone"], target=a),
            _rule(rid="r2", code="b", priority=5, contains=["iphone"], target=b),
        )
        result = classify_bundle(_bundle({"p1": _features()}, rules))
        res = result.by_product_id()["p1"].resolution
        assert res is not None
        self.assertEqual(res.status, ResolutionStatus.CONFLICT)
        self.assertIsNone(res.category_id)
        self.assertEqual(set(res.conflicting_category_ids), {"sf-a", "sf-b"})
        self.assertEqual(len(res.best_priority_matches), 2)


@override_settings(DEBUG=True)
class ClassifierOverrideTests(SimpleTestCase):
    def test_locked_override(self):
        sf = _cat("sf-locked")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=1,
                contains=["iphone"],
                target=_cat("sf-other"),
            ),
        )
        ov = OverrideInput(category=sf, is_locked=True, reason="qa")
        result = classify_bundle(
            _bundle({"p1": _features()}, rules, {"p1": ov})
        )
        res = result.by_product_id()["p1"].resolution
        assert res is not None
        self.assertEqual(res.status, ResolutionStatus.OVERRIDE)
        self.assertEqual(res.source, ResolutionSource.LOCKED_OVERRIDE)
        self.assertEqual(res.category_id, "sf-locked")

    def test_unlocked_override_plus_match_is_match(self):
        sf_rule = _cat("sf-rule")
        sf_ov = _cat("sf-ov")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=sf_rule,
            ),
        )
        ov = OverrideInput(category=sf_ov, is_locked=False)
        res = classify_bundle(
            _bundle({"p1": _features()}, rules, {"p1": ov})
        ).by_product_id()["p1"].resolution
        assert res is not None
        self.assertEqual(res.status, ResolutionStatus.MATCH)
        self.assertEqual(res.category_id, "sf-rule")
        self.assertEqual(res.source, ResolutionSource.RULE)

    def test_unlocked_override_fallback(self):
        sf = _cat("sf-fb")
        rules = (
            _rule(
                rid="r1",
                code="case",
                priority=10,
                contains=["чехол"],
                target=_cat("sf-other"),
            ),
        )
        ov = OverrideInput(category=sf, is_locked=False)
        res = classify_bundle(
            _bundle({"p1": _features()}, rules, {"p1": ov})
        ).by_product_id()["p1"].resolution
        assert res is not None
        self.assertEqual(res.status, ResolutionStatus.OVERRIDE_FALLBACK)
        self.assertEqual(res.source, ResolutionSource.OVERRIDE_FALLBACK)
        self.assertEqual(res.category_id, "sf-fb")

    def test_override_inactive_needs_review(self):
        dead = _cat("sf-dead", active=False)
        ov = OverrideInput(category=dead, is_locked=True)
        res = classify_bundle(
            _bundle({"p1": _features()}, (), {"p1": ov})
        ).by_product_id()["p1"].resolution
        assert res is not None
        self.assertEqual(res.status, ResolutionStatus.NEEDS_REVIEW)
        self.assertIsNone(res.category_id)
        self.assertIn("неактивн", res.explanation.lower())


@override_settings(DEBUG=True)
class ClassifierRulesSkipBatchTests(SimpleTestCase):
    def test_inactive_rule_ignored(self):
        sf = _cat("sf-phones")
        rules = (
            _rule(
                rid="r-dead",
                code="dead",
                priority=1,
                contains=["iphone"],
                target=sf,
                active=False,
            ),
        )
        res = classify_bundle(_bundle({"p1": _features()}, rules)).by_product_id()[
            "p1"
        ].resolution
        assert res is not None
        self.assertEqual(res.status, ResolutionStatus.UNMATCHED)
        self.assertTrue(
            any(s.reason == "inactive_rule" for s in res.skipped_rules)
        )

    def test_inactive_target_category_skipped(self):
        dead = _cat("sf-dead", active=False)
        live = _cat("sf-live")
        rules = (
            _rule(
                rid="r1",
                code="dead-tgt",
                priority=1,
                contains=["iphone"],
                target=dead,
            ),
            _rule(
                rid="r2",
                code="live",
                priority=10,
                contains=["iphone"],
                target=live,
            ),
        )
        res = classify_bundle(_bundle({"p1": _features()}, rules)).by_product_id()[
            "p1"
        ].resolution
        assert res is not None
        self.assertEqual(res.status, ResolutionStatus.MATCH)
        self.assertEqual(res.category_id, "sf-live")
        self.assertTrue(
            any(s.reason == "inactive_target_category" for s in res.skipped_rules)
        )

    def test_multiple_products_different_outcomes(self):
        rules = (
            _rule(
                rid="r1",
                code="iphone15",
                priority=10,
                contains=["iphone 15"],
                target=_cat("sf-phones"),
            ),
            _rule(
                rid="r2",
                code="pro",
                priority=10,
                contains=["pro"],
                target=_cat("sf-pro"),
            ),
            _rule(
                rid="r3",
                code="case",
                priority=10,
                contains=["чехол"],
                target=_cat("sf-acc"),
            ),
        )
        features = {
            # только r1
            "p-match": _features(title="iPhone 15"),
            "p-unmatched": _features(title="Samsung Tablet"),
            # r1 + r2, одинаковый priority, разные категории
            "p-conflict": _features(title="iPhone 15 Pro"),
        }
        result = classify_bundle(_bundle(features, rules))
        by = result.by_product_id()
        self.assertEqual(by["p-match"].resolution.status, ResolutionStatus.MATCH)
        self.assertEqual(by["p-match"].resolution.category_id, "sf-phones")
        self.assertEqual(
            by["p-unmatched"].resolution.status, ResolutionStatus.UNMATCHED
        )
        self.assertEqual(
            by["p-conflict"].resolution.status, ResolutionStatus.CONFLICT
        )
        self.assertEqual(len(result.items), 3)


@override_settings(DEBUG=True)
class ClassifierFingerprintTests(SimpleTestCase):
    def setUp(self):
        self.sf = _cat("sf-phones")
        self.rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=self.sf,
            ),
        )

    def test_same_features_same_classification_fingerprint(self):
        f = _features()
        bundle = _bundle({"a": f, "b": replace(f)}, self.rules)
        result = classify_bundle(bundle)
        fa = result.by_product_id()["a"].resolution.fingerprint
        fb = result.by_product_id()["b"].resolution.fingerprint
        self.assertEqual(fa, fb)
        self.assertEqual(
            result.by_product_id()["a"].features_fingerprint,
            result.by_product_id()["b"].features_fingerprint,
        )
        self.assertEqual(
            result.by_product_id()["a"].ruleset_fingerprint,
            result.ruleset_fingerprint,
        )

    def test_title_change_changes_fingerprint(self):
        r1 = classify_bundle(
            _bundle({"p": _features(title="iPhone 15")}, self.rules)
        ).by_product_id()["p"].resolution.fingerprint
        r2 = classify_bundle(
            _bundle({"p": _features(title="iPhone 16")}, self.rules)
        ).by_product_id()["p"].resolution.fingerprint
        self.assertNotEqual(r1, r2)

    def test_brand_change_changes_fingerprint(self):
        r1 = classify_bundle(
            _bundle({"p": _features(brand="Apple")}, self.rules)
        ).by_product_id()["p"].resolution.fingerprint
        r2 = classify_bundle(
            _bundle({"p": _features(brand="Samsung")}, self.rules)
        ).by_product_id()["p"].resolution.fingerprint
        self.assertNotEqual(r1, r2)

    def test_source_category_change_changes_fingerprint(self):
        r1 = classify_bundle(
            _bundle({"p": _features(slug="telefony", onec="00-ph")}, self.rules)
        ).by_product_id()["p"].resolution.fingerprint
        r2 = classify_bundle(
            _bundle(
                {
                    "p": _features(
                        slug="planshety",
                        onec="00-tab",
                        title_path=("Электроника", "Планшеты"),
                        slug_path=("electronics", "planshety"),
                    )
                },
                self.rules,
            )
        ).by_product_id()["p"].resolution.fingerprint
        self.assertNotEqual(r1, r2)

    def test_active_ruleset_change_changes_fingerprint(self):
        f = _features()
        r1 = classify_bundle(_bundle({"p": f}, self.rules)).by_product_id()[
            "p"
        ].resolution.fingerprint
        rules2 = self.rules + (
            _rule(
                rid="r2",
                code="pro",
                priority=20,
                contains=["pro"],
                target=self.sf,
            ),
        )
        r2 = classify_bundle(_bundle({"p": f}, rules2)).by_product_id()[
            "p"
        ].resolution.fingerprint
        self.assertNotEqual(r1, r2)
        self.assertNotEqual(
            ruleset_fingerprint(self.rules), ruleset_fingerprint(rules2)
        )

    def test_price_stock_not_in_features_fingerprint_stable(self):
        # ProductFeatures не содержит price/stock — «изменение цены» вне DTO
        # не влияет на fingerprint (архитектурная граница Classifier).
        f = _features()
        fp1 = features_fingerprint(f)
        fp2 = features_fingerprint(
            ProductFeatures(
                title=f.title,
                brand=f.brand,
                category_slug=f.category_slug,
                category_onec_code=f.category_onec_code,
                category_title_path=f.category_title_path,
                category_slug_path=f.category_slug_path,
            )
        )
        self.assertEqual(fp1, fp2)
        # classification fingerprint тоже стабилен при тех же features/rules
        c1 = classification_fingerprint(f, self.rules)
        c2 = classification_fingerprint(f, self.rules)
        self.assertEqual(c1, c2)

    def test_bundle_order_does_not_affect_item_result(self):
        sf = self.sf
        rules = self.rules
        f_match = _features(title="iPhone 15")
        f_other = _features(title="Кабель USB")
        b1 = _bundle({"z": f_other, "a": f_match}, rules)
        b2 = _bundle({"a": f_match, "z": f_other}, rules)
        r1 = classify_bundle(b1).by_product_id()
        r2 = classify_bundle(b2).by_product_id()
        self.assertEqual(r1["a"].resolution.status, r2["a"].resolution.status)
        self.assertEqual(
            r1["a"].resolution.fingerprint, r2["a"].resolution.fingerprint
        )
        self.assertEqual(r1["z"].resolution.status, r2["z"].resolution.status)
        # порядок items детерминирован по product_id
        self.assertEqual(
            [i.product_id for i in classify_bundle(b1).items],
            ["a", "z"],
        )


@override_settings(DEBUG=True)
class ClassifierErrorTests(SimpleTestCase):
    def test_fingerprint_error_is_technical_not_business(self):
        sf = _cat("sf")
        # object() в payload → FingerprintError на ruleset уровне → ClassifierError
        bad_rule = RuleInput(
            id="bad",
            code="bad",
            priority=1,
            is_active=True,
            condition_type=CONDITION_TITLE_CONTAINS,
            condition_payload={"contains": ["x"], "x": object()},  # type: ignore[dict-item]
            schema_version=1,
            target_category=sf,
        )
        with self.assertRaises(ClassifierError) as ctx:
            classify_bundle(_bundle({"p1": _features()}, (bad_rule,)))
        self.assertIn("ruleset fingerprint", str(ctx.exception).lower())

    def test_per_item_fingerprint_error_not_business_status(self):
        sf = _cat("sf")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=sf,
            ),
        )
        # Fail features_fingerprint for product "bad" only
        real_ff = features_fingerprint

        def selective(features, **kwargs):
            # после normalize_features brand уже casefold
            if getattr(features, "brand", None) == "bad":
                raise FingerprintError("forced features fp failure")
            return real_ff(features, **kwargs)

        bundle = _bundle(
            {
                "ok": _features(brand="Apple"),
                "bad": _features(brand="BAD"),
            },
            rules,
        )
        with patch(
            "apps.storefront_taxonomy.engine.classifier.features_fingerprint",
            side_effect=selective,
        ):
            result = classify_bundle(bundle)
        ok = result.by_product_id()["ok"]
        bad = result.by_product_id()["bad"]
        self.assertEqual(ok.outcome, ItemOutcome.RESOLVED)
        self.assertEqual(ok.resolution.status, ResolutionStatus.MATCH)
        self.assertEqual(bad.outcome, ItemOutcome.ERROR)
        self.assertIsNone(bad.resolution)
        self.assertEqual(bad.error_type, "FingerprintError")
        self.assertIsNotNone(bad.error_message)
        # ERROR не маскируется бизнес-статусом
        self.assertNotIn(
            bad.error_type or "",
            {s.value for s in ResolutionStatus},
        )

    def test_resolver_error_is_technical(self):
        sf = _cat("sf")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=sf,
            ),
        )
        bundle = _bundle(
            {"ok": _features(), "bad": _features(title="Other")},
            rules,
        )

        real_resolve = __import__(
            "apps.storefront_taxonomy.engine.resolver", fromlist=["resolve"]
        ).resolve

        def selective_resolve(features, rules, override=None, **kwargs):
            # NormalizedFeatures.title уже casefold
            if getattr(features, "title", "") == "other":
                raise ValueError("forced resolver failure")
            return real_resolve(features, rules, override, **kwargs)

        with patch(
            "apps.storefront_taxonomy.engine.classifier.resolve",
            side_effect=selective_resolve,
        ):
            result = classify_bundle(bundle)
        self.assertEqual(
            result.by_product_id()["ok"].outcome, ItemOutcome.RESOLVED
        )
        bad = result.by_product_id()["bad"]
        self.assertEqual(bad.outcome, ItemOutcome.ERROR)
        self.assertEqual(bad.error_type, "ValueError")
        self.assertIn("forced resolver failure", bad.error_message or "")
        self.assertIsNone(bad.resolution)

    def test_invalid_bundle_raises_classifier_error(self):
        with self.assertRaises(ClassifierError):
            classify_bundle(None)
        with self.assertRaises(ClassifierError):
            classify_bundle(SimpleNamespace())
        with self.assertRaises(ClassifierError):
            classify_bundle(
                SimpleNamespace(
                    features_by_product_id="nope",
                    rules=(),
                    overrides_by_product_id={},
                )
            )
        with self.assertRaises(ClassifierError):
            classify_bundle(
                SimpleNamespace(
                    features_by_product_id={},
                    rules="not-a-sequence",
                    overrides_by_product_id={},
                )
            )

    def test_one_item_error_keeps_others(self):
        sf = _cat("sf")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=sf,
            ),
        )
        bundle = _bundle(
            {
                "p1": _features(),
                "p2": "not-features",  # type: ignore[dict-item]
                "p3": _features(title="iPhone SE"),
            },
            rules,
        )
        result = classify_bundle(bundle)
        by = result.by_product_id()
        self.assertEqual(by["p1"].outcome, ItemOutcome.RESOLVED)
        self.assertEqual(by["p3"].outcome, ItemOutcome.RESOLVED)
        self.assertEqual(by["p2"].outcome, ItemOutcome.ERROR)
        self.assertEqual(by["p2"].error_type, "TypeError")
        self.assertIn("ProductFeatures", by["p2"].error_message or "")

    def test_error_diagnostics_for_dry_run(self):
        bundle = _bundle(
            {"x": 123},  # type: ignore[dict-item]
            (),
        )
        item = classify_bundle(bundle).items[0]
        self.assertEqual(item.outcome, ItemOutcome.ERROR)
        self.assertEqual(item.product_id, "x")
        self.assertTrue(item.error_type)
        self.assertTrue(item.error_message)
        self.assertIsNone(item.resolution)


@override_settings(DEBUG=True)
class ClassifierReadOnlyDeterminismTests(SimpleTestCase):
    def test_no_sql_queries(self):
        sf = _cat("sf")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=sf,
            ),
        )
        bundle = _bundle({"p1": _features()}, rules)
        reset_queries()
        classify_bundle(bundle)
        self.assertEqual(len(connection.queries), 0)

    def test_does_not_mutate_input_dto(self):
        sf = _cat("sf")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=sf,
            ),
        )
        features = {"p1": _features()}
        overrides: dict[str, OverrideInput] = {}
        bundle = _bundle(features, rules, overrides)
        before_rules = deepcopy(
            [
                (
                    r.id,
                    r.code,
                    r.priority,
                    r.is_active,
                    deepcopy(r.condition_payload),
                )
                for r in bundle.rules
            ]
        )
        before_feat = bundle.features_by_product_id["p1"]
        classify_bundle(bundle)
        self.assertEqual(
            [
                (
                    r.id,
                    r.code,
                    r.priority,
                    r.is_active,
                    r.condition_payload,
                )
                for r in bundle.rules
            ],
            before_rules,
        )
        self.assertIs(bundle.features_by_product_id["p1"], before_feat)
        self.assertEqual(bundle.overrides_by_product_id, {})

    def test_repeatable_results(self):
        sf = _cat("sf")
        rules = (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=sf,
            ),
            _rule(
                rid="r2",
                code="alt",
                priority=10,
                contains=["iphone"],
                target=_cat("sf-alt"),
            ),
        )
        bundle = _bundle(
            {
                "b": _features(title="Cable"),
                "a": _features(),
            },
            rules,
            {
                "b": OverrideInput(
                    category=_cat("sf-fb"), is_locked=False
                ),
            },
        )
        r1 = classify_bundle(bundle)
        r2 = classify_bundle(bundle)
        self.assertEqual(r1.ruleset_fingerprint, r2.ruleset_fingerprint)
        self.assertEqual(
            [(i.product_id, i.outcome, i.resolution.status if i.resolution else None,
              i.resolution.fingerprint if i.resolution else None,
              i.error_type) for i in r1.items],
            [(i.product_id, i.outcome, i.resolution.status if i.resolution else None,
              i.resolution.fingerprint if i.resolution else None,
              i.error_type) for i in r2.items],
        )

    def test_classifier_module_has_no_orm_imports(self):
        import apps.storefront_taxonomy.engine.classifier as mod

        with open(mod.__file__, encoding="utf-8") as fh:
            src = fh.read()
        import_lines = [
            line
            for line in src.splitlines()
            if line.lstrip().startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines)
        self.assertNotIn("django.db", joined)
        self.assertNotIn("apps.products", joined)
        self.assertNotIn("adapters", joined)
        self.assertNotIn("storefront_taxonomy.models", joined)
        self.assertNotIn(".save(", src)
        self.assertNotIn("bulk_create", src)
        self.assertNotIn("bulk_update", src)

    def test_classifier_error_not_subclass_of_value_error(self):
        self.assertFalse(issubclass(ClassifierError, ValueError))
        self.assertTrue(issubclass(ClassifierError, Exception))


@override_settings(DEBUG=True)
class ClassifierOptimizationAndIsolationTests(SimpleTestCase):
    """S1.2.4.3: счётчики fingerprint и изоляция ошибок."""

    def _rules(self):
        return (
            _rule(
                rid="r1",
                code="iphone",
                priority=10,
                contains=["iphone"],
                target=_cat("sf"),
            ),
        )

    def _probe_counts(self, n: int) -> dict[str, int]:
        counts = {
            "ruleset": 0,
            "features": 0,
            "normalize": 0,
            "classification": 0,
            "combine": 0,
        }
        real_rs = fingerprint_mod.ruleset_fingerprint
        real_ff = fingerprint_mod.features_fingerprint
        real_cf = fingerprint_mod.classification_fingerprint
        real_combine = fingerprint_mod.combine_classification_fingerprint
        real_nf = normalizers_mod.normalize_features

        def wrap_rs(rules):
            counts["ruleset"] += 1
            return real_rs(rules)

        def wrap_ff(features, **kwargs):
            counts["features"] += 1
            return real_ff(features, **kwargs)

        def wrap_cf(features, rules, **kwargs):
            counts["classification"] += 1
            return real_cf(features, rules, **kwargs)

        def wrap_combine(features_fp, ruleset_fp):
            counts["combine"] += 1
            return real_combine(features_fp, ruleset_fp)

        def wrap_nf(features):
            counts["normalize"] += 1
            return real_nf(features)

        features = {f"p{i:03d}": _features(title=f"iPhone {i}") for i in range(n)}
        bundle = _bundle(features, self._rules())

        with (
            patch.object(fingerprint_mod, "ruleset_fingerprint", side_effect=wrap_rs),
            patch.object(fingerprint_mod, "features_fingerprint", side_effect=wrap_ff),
            patch.object(
                fingerprint_mod, "classification_fingerprint", side_effect=wrap_cf
            ),
            patch.object(
                fingerprint_mod,
                "combine_classification_fingerprint",
                side_effect=wrap_combine,
            ),
            patch.object(normalizers_mod, "normalize_features", side_effect=wrap_nf),
            patch.object(classifier_mod, "ruleset_fingerprint", side_effect=wrap_rs),
            patch.object(classifier_mod, "features_fingerprint", side_effect=wrap_ff),
            patch.object(
                classifier_mod,
                "combine_classification_fingerprint",
                side_effect=wrap_combine,
            ),
            patch.object(classifier_mod, "normalize_features", side_effect=wrap_nf),
        ):
            result = classify_bundle(bundle)

        self.assertEqual(len(result.items), n)
        # идентичность старой формуле
        for item in result.items:
            raw = features[item.product_id]
            self.assertEqual(
                item.resolution.fingerprint,
                classification_fingerprint(raw, self._rules()),
            )
            self.assertEqual(
                item.resolution.fingerprint,
                combine_classification_fingerprint(
                    item.features_fingerprint, result.ruleset_fingerprint
                ),
            )
        return counts

    def test_fingerprint_counters_n1(self):
        c = self._probe_counts(1)
        self.assertEqual(c["ruleset"], 1)
        self.assertEqual(c["features"], 1)
        self.assertEqual(c["normalize"], 1)
        self.assertEqual(c["classification"], 0)
        self.assertEqual(c["combine"], 1)

    def test_fingerprint_counters_n5(self):
        c = self._probe_counts(5)
        self.assertEqual(c["ruleset"], 1)
        self.assertEqual(c["features"], 5)
        self.assertEqual(c["normalize"], 5)
        self.assertEqual(c["classification"], 0)
        self.assertEqual(c["combine"], 5)

    def test_fingerprint_counters_n100(self):
        c = self._probe_counts(100)
        self.assertEqual(c["ruleset"], 1)
        self.assertEqual(c["features"], 100)
        self.assertEqual(c["normalize"], 100)
        self.assertEqual(c["classification"], 0)
        self.assertEqual(c["combine"], 100)

    def test_keyerror_isolates_one_item(self):
        rules = self._rules()
        bundle = _bundle(
            {"ok": _features(), "bad": _features(title="iPhone X")},
            rules,
        )
        real_nf = normalizers_mod.normalize_features

        def selective_nf(features):
            if features.title == "iPhone X":
                raise KeyError("forced-missing-field")
            return real_nf(features)

        with patch.object(
            classifier_mod, "normalize_features", side_effect=selective_nf
        ):
            result = classify_bundle(bundle)
        self.assertEqual(result.by_product_id()["ok"].outcome, ItemOutcome.RESOLVED)
        bad = result.by_product_id()["bad"]
        self.assertEqual(bad.outcome, ItemOutcome.ERROR)
        self.assertEqual(bad.error_type, "KeyError")
        self.assertIsNone(bad.resolution)

    def test_classifier_error_in_item_loop_rethrows(self):
        rules = self._rules()
        bundle = _bundle(
            {"a": _features(), "b": _features(title="Boom")},
            rules,
        )
        real_nf = normalizers_mod.normalize_features

        def selective_nf(features):
            if features.title == "Boom":
                raise ClassifierError("should-abort-batch")
            return real_nf(features)

        with patch.object(
            classifier_mod, "normalize_features", side_effect=selective_nf
        ):
            with self.assertRaises(ClassifierError) as ctx:
                classify_bundle(bundle)
        self.assertIn("should-abort-batch", str(ctx.exception))
