"""S1.2.3 / S1.2.4.3: unit-тесты Resolver."""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.storefront_taxonomy.engine.fingerprint import classification_fingerprint
from apps.storefront_taxonomy.engine.normalizers import (
    ProductFeatures,
    normalize_features,
)
from apps.storefront_taxonomy.engine.resolution_types import (
    CategoryRef,
    OverrideInput,
    ResolutionSource,
    ResolutionStatus,
    RuleInput,
)
from apps.storefront_taxonomy.engine.resolver import resolve


def _cat(cid: str, *, active: bool = True, slug: str = "") -> CategoryRef:
    return CategoryRef(id=cid, is_active=active, slug=slug or cid)


def _rule(
    code: str,
    *,
    priority: int = 100,
    category: CategoryRef | None = None,
    contains: list[str] | None = None,
    active: bool = True,
    target_active: bool = True,
    condition_type: str = "title_contains",
    payload: dict | None = None,
    schema_version: int = 1,
    rule_id: str | None = None,
) -> RuleInput:
    cat = category or _cat("cat-default", active=target_active)
    if category is None and not target_active:
        cat = _cat(cat.id, active=False, slug=cat.slug)
    elif category is not None and not target_active:
        cat = _cat(category.id, active=False, slug=category.slug)
    pl = payload
    if pl is None:
        pl = {"contains": contains or ["iphone"]}
    return RuleInput(
        id=rule_id or f"id-{code}",
        code=code,
        priority=priority,
        is_active=active,
        condition_type=condition_type,
        condition_payload=pl,
        schema_version=schema_version,
        target_category=cat,
    )


def _features(**kwargs) -> ProductFeatures:
    base = dict(
        title="Apple iPhone 15",
        brand="Apple",
        category_slug="telefony",
        category_onec_code="00-ph",
        category_title_path=("Телефоны",),
        category_slug_path=("telefony",),
    )
    base.update(kwargs)
    return ProductFeatures(**base)


class ResolverCoreTests(SimpleTestCase):
    def test_no_matches_no_override(self):
        result = resolve(
            _features(title="Чехол"),
            [_rule("r1", contains=["iphone"])],
        )
        self.assertEqual(result.status, ResolutionStatus.UNMATCHED)
        self.assertIsNone(result.category_id)
        self.assertEqual(result.source, ResolutionSource.NONE)

    def test_single_match(self):
        cat = _cat("cat-phones")
        result = resolve(_features(), [_rule("r1", priority=10, category=cat)])
        self.assertEqual(result.status, ResolutionStatus.MATCH)
        self.assertEqual(result.category_id, "cat-phones")
        self.assertEqual(result.winning_rule_code, "r1")
        self.assertEqual(result.winning_priority, 10)
        self.assertEqual(result.source, ResolutionSource.RULE)

    def test_multiple_same_category(self):
        cat = _cat("cat-a")
        result = resolve(
            _features(),
            [
                _rule("a", priority=5, category=cat, contains=["iphone"]),
                _rule("b", priority=5, category=cat, contains=["apple"]),
            ],
        )
        self.assertEqual(result.status, ResolutionStatus.MATCH)
        self.assertEqual(result.category_id, "cat-a")
        self.assertEqual(len(result.best_priority_matches), 2)

    def test_conflict_different_categories(self):
        result = resolve(
            _features(),
            [
                _rule("a", priority=5, category=_cat("c1"), contains=["iphone"]),
                _rule("b", priority=5, category=_cat("c2"), contains=["apple"]),
            ],
        )
        self.assertEqual(result.status, ResolutionStatus.CONFLICT)
        self.assertIsNone(result.category_id)
        self.assertEqual(result.conflicting_category_ids, ("c1", "c2"))
        self.assertEqual(len(result.best_priority_matches), 2)

    def test_lower_priority_does_not_mask_conflict(self):
        result = resolve(
            _features(),
            [
                _rule("a", priority=1, category=_cat("c1"), contains=["iphone"]),
                _rule("b", priority=1, category=_cat("c2"), contains=["apple"]),
                _rule("c", priority=50, category=_cat("c1"), contains=["iphone"]),
            ],
        )
        self.assertEqual(result.status, ResolutionStatus.CONFLICT)
        self.assertEqual(result.conflicting_category_ids, ("c1", "c2"))
        self.assertTrue(all(m.priority == 1 for m in result.best_priority_matches))

    def test_smaller_priority_number_wins(self):
        result = resolve(
            _features(),
            [
                _rule("low", priority=100, category=_cat("c-low"), contains=["iphone"]),
                _rule("high", priority=10, category=_cat("c-high"), contains=["iphone"]),
            ],
        )
        self.assertEqual(result.status, ResolutionStatus.MATCH)
        self.assertEqual(result.category_id, "c-high")
        self.assertEqual(result.winning_rule_code, "high")

    def test_empty_rules(self):
        result = resolve(_features(), [])
        self.assertEqual(result.status, ResolutionStatus.UNMATCHED)


class ResolverOverrideTests(SimpleTestCase):
    def test_locked_override(self):
        result = resolve(
            _features(),
            [_rule("r1", category=_cat("from-rule"))],
            OverrideInput(category=_cat("from-ovr"), is_locked=True),
        )
        self.assertEqual(result.status, ResolutionStatus.OVERRIDE)
        self.assertEqual(result.category_id, "from-ovr")
        self.assertEqual(result.source, ResolutionSource.LOCKED_OVERRIDE)

    def test_locked_override_inactive_category(self):
        result = resolve(
            _features(),
            [_rule("r1", category=_cat("from-rule"))],
            OverrideInput(category=_cat("dead", active=False), is_locked=True),
        )
        self.assertEqual(result.status, ResolutionStatus.NEEDS_REVIEW)
        self.assertIsNone(result.category_id)

    def test_unlocked_override_plus_match(self):
        result = resolve(
            _features(),
            [_rule("r1", category=_cat("from-rule"))],
            OverrideInput(category=_cat("from-ovr"), is_locked=False),
        )
        self.assertEqual(result.status, ResolutionStatus.MATCH)
        self.assertEqual(result.category_id, "from-rule")
        self.assertEqual(result.source, ResolutionSource.RULE)

    def test_unlocked_override_fallback_when_unmatched(self):
        result = resolve(
            _features(title="Чехол"),
            [_rule("r1", contains=["iphone"])],
            OverrideInput(category=_cat("from-ovr"), is_locked=False),
        )
        self.assertEqual(result.status, ResolutionStatus.OVERRIDE_FALLBACK)
        self.assertEqual(result.category_id, "from-ovr")
        self.assertEqual(result.source, ResolutionSource.OVERRIDE_FALLBACK)

    def test_unlocked_override_does_not_hide_conflict(self):
        result = resolve(
            _features(),
            [
                _rule("a", priority=5, category=_cat("c1")),
                _rule("b", priority=5, category=_cat("c2"), contains=["apple"]),
            ],
            OverrideInput(category=_cat("from-ovr"), is_locked=False),
        )
        self.assertEqual(result.status, ResolutionStatus.CONFLICT)

    def test_unlocked_override_inactive_needs_review(self):
        result = resolve(
            _features(title="Чехол"),
            [_rule("r1", contains=["iphone"])],
            OverrideInput(category=_cat("dead", active=False), is_locked=False),
        )
        self.assertEqual(result.status, ResolutionStatus.NEEDS_REVIEW)


class ResolverErrorAndSkipTests(SimpleTestCase):
    def test_inactive_target_category_skipped(self):
        result = resolve(
            _features(),
            [
                _rule("bad-target", category=_cat("x", active=False), contains=["iphone"]),
                _rule("ok", priority=20, category=_cat("ok-cat"), contains=["iphone"]),
            ],
        )
        self.assertEqual(result.status, ResolutionStatus.MATCH)
        self.assertEqual(result.category_id, "ok-cat")
        self.assertTrue(
            any(s.reason == "inactive_target_category" for s in result.skipped_rules)
        )

    def test_invalid_rule_among_valid(self):
        result = resolve(
            _features(),
            [
                _rule(
                    "broken",
                    priority=1,
                    condition_type="title_regex",
                    payload={"pattern": "("},
                    category=_cat("c-broken"),
                ),
                _rule("ok", priority=10, category=_cat("c-ok"), contains=["iphone"]),
            ],
        )
        self.assertEqual(result.status, ResolutionStatus.MATCH)
        self.assertEqual(result.category_id, "c-ok")
        self.assertEqual(len(result.rule_errors), 1)
        self.assertEqual(result.rule_errors[0].code, "broken")
        self.assertEqual(result.rule_errors[0].error_type, "InvalidRegexError")

    def test_multiple_invalid_rules(self):
        result = resolve(
            _features(),
            [
                _rule(
                    "b1",
                    condition_type="title_regex",
                    payload={"pattern": "("},
                ),
                _rule(
                    "b2",
                    condition_type="title_contains",
                    payload={"contains": []},
                ),
            ],
        )
        self.assertEqual(result.status, ResolutionStatus.UNMATCHED)
        self.assertEqual(len(result.rule_errors), 2)
        codes = [e.code for e in result.rule_errors]
        self.assertEqual(codes, sorted(codes))

    def test_invalid_rule_does_not_produce_fake_match(self):
        result = resolve(
            _features(),
            [
                _rule(
                    "broken",
                    priority=1,
                    condition_type="title_regex",
                    payload={"pattern": "(a+)+"},
                    category=_cat("c-broken"),
                ),
            ],
        )
        self.assertNotEqual(result.status, ResolutionStatus.MATCH)
        self.assertIsNone(result.category_id)
        self.assertEqual(len(result.rule_errors), 1)

    def test_diagnostics_order_deterministic(self):
        r1 = resolve(
            _features(),
            [
                _rule("z", condition_type="title_regex", payload={"pattern": "("}),
                _rule("a", condition_type="title_contains", payload={"contains": []}),
            ],
        )
        r2 = resolve(
            _features(),
            [
                _rule("a", condition_type="title_contains", payload={"contains": []}),
                _rule("z", condition_type="title_regex", payload={"pattern": "("}),
            ],
        )
        self.assertEqual(
            [(e.code, e.error_type) for e in r1.rule_errors],
            [(e.code, e.error_type) for e in r2.rule_errors],
        )
        self.assertEqual(r1.fingerprint, r2.fingerprint)


class ResolverFingerprintKwTests(SimpleTestCase):
    """S1.2.4.3: публичный контракт + optional fingerprint=."""

    def test_public_resolve_fingerprint_matches_classification_formula(self):
        feats = _features()
        rules = [_rule("r1", priority=10, category=_cat("cat-phones"))]
        result = resolve(feats, rules)
        self.assertEqual(result.status, ResolutionStatus.MATCH)
        self.assertEqual(
            result.fingerprint,
            classification_fingerprint(feats, rules),
        )

    def test_precomputed_fingerprint_used_without_recompute(self):
        feats = _features()
        rules = [_rule("r1", priority=10, category=_cat("cat-phones"))]
        expected = classification_fingerprint(feats, rules)
        with patch(
            "apps.storefront_taxonomy.engine.resolver.classification_fingerprint"
        ) as mocked:
            result = resolve(feats, rules, fingerprint=expected)
            mocked.assert_not_called()
        self.assertEqual(result.fingerprint, expected)
        self.assertEqual(result.status, ResolutionStatus.MATCH)

    def test_normalized_features_same_match_as_raw(self):
        raw = _features()
        rules = [_rule("r1", priority=10, category=_cat("cat-phones"))]
        r1 = resolve(raw, rules)
        r2 = resolve(normalize_features(raw), rules)
        self.assertEqual(r1.status, r2.status)
        self.assertEqual(r1.category_id, r2.category_id)
        self.assertEqual(r1.fingerprint, r2.fingerprint)
