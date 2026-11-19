"""S1.2.3 / S1.2.3.1: unit-тесты fingerprint."""

from __future__ import annotations

from typing import Any

from django.test import SimpleTestCase

from apps.storefront_taxonomy.engine.fingerprint import (
    PAYLOAD_KIND_KEY,
    classification_fingerprint,
    combine_classification_fingerprint,
    encode_condition_payload_for_fingerprint,
    features_fingerprint,
    ruleset_fingerprint,
)
from apps.storefront_taxonomy.engine.normalizers import ProductFeatures
from apps.storefront_taxonomy.engine.resolution_types import CategoryRef, RuleInput


def _cat(cid: str = "c1", *, active: bool = True) -> CategoryRef:
    return CategoryRef(id=cid, is_active=active, slug=cid)


def _rule(**kwargs: Any) -> RuleInput:
    defaults: dict[str, Any] = dict(
        id="rid-1",
        code="rule-a",
        priority=10,
        is_active=True,
        condition_type="title_contains",
        condition_payload={"contains": ["iphone"], "match": "any"},
        schema_version=1,
        target_category=_cat(),
    )
    defaults.update(kwargs)
    return RuleInput(**defaults)


def _features(**kwargs: Any) -> ProductFeatures:
    base: dict[str, Any] = dict(
        title="iPhone 15",
        brand="Apple",
        category_slug="telefony",
        category_onec_code="00-1",
        category_title_path=("Телефоны", "Apple"),
        category_slug_path=("telefony", "apple"),
    )
    base.update(kwargs)
    return ProductFeatures(**base)


def _fp(payload: Any, *, condition_type: str = "title_contains") -> str:
    return ruleset_fingerprint(
        [_rule(condition_type=condition_type, condition_payload=payload)]
    )


class FeaturesFingerprintTests(SimpleTestCase):
    def test_same_input_same_fingerprint(self):
        a = features_fingerprint(_features())
        b = features_fingerprint(_features())
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_title_change(self):
        self.assertNotEqual(
            features_fingerprint(_features(title="iPhone 15")),
            features_fingerprint(_features(title="iPhone 16")),
        )

    def test_brand_change(self):
        self.assertNotEqual(
            features_fingerprint(_features(brand="Apple")),
            features_fingerprint(_features(brand="Samsung")),
        )

    def test_category_change(self):
        self.assertNotEqual(
            features_fingerprint(_features(category_slug="telefony")),
            features_fingerprint(_features(category_slug="aksessuary")),
        )
        self.assertNotEqual(
            features_fingerprint(_features(category_onec_code="00-1")),
            features_fingerprint(_features(category_onec_code="00-2")),
        )
        self.assertNotEqual(
            features_fingerprint(_features(category_title_path=("A",))),
            features_fingerprint(_features(category_title_path=("B",))),
        )

    def test_optional_brand_stable(self):
        self.assertEqual(
            features_fingerprint(_features(brand=None)),
            features_fingerprint(_features(brand="")),
        )

    def test_normalizer_version_changes_fingerprint(self):
        feats = _features()
        self.assertNotEqual(
            features_fingerprint(feats, normalizer_version=1),
            features_fingerprint(feats, normalizer_version=2),
        )

    def test_price_stock_updated_at_not_in_features_model(self):
        self.assertEqual(features_fingerprint(_features()), features_fingerprint(_features()))


class RulesetFingerprintTests(SimpleTestCase):
    def test_rule_order_irrelevant(self):
        r1 = _rule(id="1", code="a", priority=10)
        r2 = _rule(id="2", code="b", priority=20, condition_payload={"contains": ["x"]})
        self.assertEqual(ruleset_fingerprint([r1, r2]), ruleset_fingerprint([r2, r1]))

    def test_payload_key_order_irrelevant(self):
        a = _rule(condition_payload={"match": "any", "contains": ["iphone", "apple"]})
        b = _rule(condition_payload={"contains": ["apple", "iphone"], "match": "any"})
        self.assertEqual(ruleset_fingerprint([a]), ruleset_fingerprint([b]))

    def test_priority_change(self):
        self.assertNotEqual(
            ruleset_fingerprint([_rule(priority=10)]),
            ruleset_fingerprint([_rule(priority=11)]),
        )

    def test_payload_change(self):
        self.assertNotEqual(
            ruleset_fingerprint([_rule(condition_payload={"contains": ["iphone"]})]),
            ruleset_fingerprint([_rule(condition_payload={"contains": ["samsung"]})]),
        )

    def test_target_category_change(self):
        self.assertNotEqual(
            ruleset_fingerprint([_rule(target_category=_cat("c1"))]),
            ruleset_fingerprint([_rule(target_category=_cat("c2"))]),
        )

    def test_target_active_status_change(self):
        self.assertNotEqual(
            ruleset_fingerprint([_rule(target_category=_cat("c1", active=True))]),
            ruleset_fingerprint([_rule(target_category=_cat("c1", active=False))]),
        )

    def test_inactive_rule_ignored(self):
        active = _rule(id="1", code="a")
        inactive = _rule(
            id="2",
            code="b",
            is_active=False,
            priority=1,
            condition_payload={"contains": ["zzz"]},
        )
        self.assertEqual(
            ruleset_fingerprint([active]),
            ruleset_fingerprint([active, inactive]),
        )

    def test_classification_combines_features_and_rules(self):
        rules = [_rule()]
        fp1 = classification_fingerprint(_features(title="A"), rules)
        fp2 = classification_fingerprint(_features(title="B"), rules)
        self.assertNotEqual(fp1, fp2)
        self.assertEqual(
            classification_fingerprint(_features(), rules),
            classification_fingerprint(_features(), list(reversed(rules))),
        )

    def test_combine_matches_classification_fingerprint(self):
        feats = _features()
        rules = [_rule()]
        ffp = features_fingerprint(feats)
        rfp = ruleset_fingerprint(rules)
        self.assertEqual(
            combine_classification_fingerprint(ffp, rfp),
            classification_fingerprint(feats, rules),
        )

    def test_classification_fingerprint_reuses_precomputed_parts(self):
        feats = _features()
        rules = [_rule()]
        ffp = features_fingerprint(feats)
        rfp = ruleset_fingerprint(rules)
        self.assertEqual(
            classification_fingerprint(feats, rules, features_fp=ffp, ruleset_fp=rfp),
            classification_fingerprint(feats, rules),
        )
        self.assertEqual(
            classification_fingerprint(feats, rules, features_fp=ffp),
            classification_fingerprint(feats, rules),
        )
        self.assertEqual(
            classification_fingerprint(feats, rules, ruleset_fp=rfp),
            classification_fingerprint(feats, rules),
        )


class PayloadIntegrityTypeTests(SimpleTestCase):
    """S1.2.3.1: non-dict / invalid dict больше не схлопываются в {}."""

    def test_none_differs_from_empty_string(self):
        self.assertNotEqual(_fp(None), _fp(""))

    def test_none_differs_from_empty_dict(self):
        self.assertNotEqual(_fp(None), _fp({}))

    def test_none_differs_from_empty_list(self):
        self.assertNotEqual(_fp(None), _fp([]))

    def test_string_differs_from_list(self):
        self.assertNotEqual(_fp("x"), _fp(["x"]))

    def test_list_differs_from_dict(self):
        self.assertNotEqual(_fp(["x"]), _fp({"contains": ["x"]}))

    def test_int_differs_from_bool(self):
        self.assertNotEqual(_fp(1), _fp(True))
        self.assertNotEqual(_fp(0), _fp(False))

    def test_empty_dict_differs_from_unknown_key_dict(self):
        self.assertNotEqual(_fp({}), _fp({"extra": 1}))

    def test_tagged_kinds_for_non_dict(self):
        self.assertEqual(
            encode_condition_payload_for_fingerprint("title_contains", None),
            {PAYLOAD_KIND_KEY: "null"},
        )
        self.assertEqual(
            encode_condition_payload_for_fingerprint("title_contains", "broken"),
            {PAYLOAD_KIND_KEY: "str", "value": "broken"},
        )
        self.assertEqual(
            encode_condition_payload_for_fingerprint("title_contains", ["x"]),
            {PAYLOAD_KIND_KEY: "list", "value": ["x"]},
        )
        enc_empty = encode_condition_payload_for_fingerprint("title_contains", {})
        self.assertEqual(enc_empty[PAYLOAD_KIND_KEY], "dict_invalid")
        self.assertEqual(enc_empty["value"], {})


class PayloadIntegrityContentTests(SimpleTestCase):
    def test_string_content_change(self):
        self.assertNotEqual(_fp("broken"), _fp("broken2"))

    def test_list_element_change(self):
        self.assertNotEqual(_fp(["a"]), _fp(["b"]))

    def test_nested_dict_value_change(self):
        self.assertNotEqual(
            _fp({"contains": ["iphone"], "extra": {"a": 1}}),
            _fp({"contains": ["iphone"], "extra": {"a": 2}}),
        )

    def test_wrong_type_value_change_on_known_key(self):
        self.assertNotEqual(
            _fp({"contains": "iphone"}),
            _fp({"contains": "samsung"}),
        )
        self.assertNotEqual(
            _fp({"contains": "iphone"}),
            _fp({"contains": ["iphone"]}),
        )

    def test_repeatability(self):
        for payload in (None, "x", ["a", "b"], {"foo": 1}, 123, False):
            self.assertEqual(_fp(payload), _fp(payload))


class ValidPayloadSemanticsRegressionTests(SimpleTestCase):
    def test_contains_order_irrelevant(self):
        self.assertEqual(
            _fp({"contains": ["iphone", "apple"], "match": "any"}),
            _fp({"contains": ["apple", "iphone"], "match": "any"}),
        )

    def test_brands_order_irrelevant(self):
        self.assertEqual(
            _fp(
                {"brands": ["Apple", "Samsung"]},
                condition_type="brand_equals",
            ),
            _fp(
                {"brands": ["Samsung", "Apple"]},
                condition_type="brand_equals",
            ),
        )

    def test_slugs_order_irrelevant(self):
        self.assertEqual(
            _fp(
                {"slugs": ["a", "b"], "mode": "exact"},
                condition_type="onec_category_slug",
            ),
            _fp(
                {"slugs": ["b", "a"], "mode": "exact"},
                condition_type="onec_category_slug",
            ),
        )

    def test_path_segments_order_matters(self):
        self.assertNotEqual(
            _fp(
                {
                    "source": "title_path",
                    "segments": ["A", "B"],
                    "mode": "exact",
                },
                condition_type="onec_category_path",
            ),
            _fp(
                {
                    "source": "title_path",
                    "segments": ["B", "A"],
                    "mode": "exact",
                },
                condition_type="onec_category_path",
            ),
        )

    def test_composite_and_or_sibling_order_irrelevant(self):
        a = {
            "op": "and",
            "args": [
                {"type": "title_contains", "payload": {"contains": ["a"]}},
                {"type": "title_contains", "payload": {"contains": ["b"]}},
            ],
        }
        b = {
            "op": "and",
            "args": [
                {"type": "title_contains", "payload": {"contains": ["b"]}},
                {"type": "title_contains", "payload": {"contains": ["a"]}},
            ],
        }
        self.assertEqual(
            _fp(a, condition_type="composite"),
            _fp(b, condition_type="composite"),
        )

    def test_valid_payload_encode_has_no_kind_wrapper(self):
        enc = encode_condition_payload_for_fingerprint(
            "title_contains",
            {"contains": ["iphone"], "match": "any"},
        )
        self.assertNotIn(PAYLOAD_KIND_KEY, enc)
        self.assertEqual(enc["contains"], ["iphone"])


class CompositeLeafIntegrityTests(SimpleTestCase):
    def _composite_with_leaf_payload(self, leaf_payload: Any) -> dict:
        node: dict[str, Any] = {
            "type": "title_contains",
        }
        if leaf_payload is not Ellipsis:
            node["payload"] = leaf_payload
        return {"op": "and", "args": [node]}

    def test_missing_leaf_payload_differs_from_null(self):
        missing = self._composite_with_leaf_payload(Ellipsis)
        # remove key entirely
        missing = {"op": "and", "args": [{"type": "title_contains"}]}
        null_pl = self._composite_with_leaf_payload(None)
        self.assertNotEqual(
            _fp(missing, condition_type="composite"),
            _fp(null_pl, condition_type="composite"),
        )

    def test_leaf_null_differs_from_empty_dict(self):
        self.assertNotEqual(
            _fp(self._composite_with_leaf_payload(None), condition_type="composite"),
            _fp(self._composite_with_leaf_payload({}), condition_type="composite"),
        )

    def test_leaf_string_differs_from_list(self):
        self.assertNotEqual(
            _fp(self._composite_with_leaf_payload("x"), condition_type="composite"),
            _fp(self._composite_with_leaf_payload(["x"]), condition_type="composite"),
        )

    def test_leaf_string_content_change(self):
        self.assertNotEqual(
            _fp(self._composite_with_leaf_payload("a"), condition_type="composite"),
            _fp(self._composite_with_leaf_payload("b"), condition_type="composite"),
        )

    def test_leaf_wrong_value_change(self):
        self.assertNotEqual(
            _fp(
                self._composite_with_leaf_payload({"contains": "iphone"}),
                condition_type="composite",
            ),
            _fp(
                self._composite_with_leaf_payload({"contains": "samsung"}),
                condition_type="composite",
            ),
        )

    def test_not_two_args_is_invalid_and_stable(self):
        # NOT с двумя args отклоняется схемой → dict_invalid, но детерминированно
        bad = {
            "op": "not",
            "args": [
                {"type": "title_contains", "payload": {"contains": ["a"]}},
                {"type": "title_contains", "payload": {"contains": ["b"]}},
            ],
        }
        enc = encode_condition_payload_for_fingerprint("composite", bad)
        self.assertEqual(enc[PAYLOAD_KIND_KEY], "dict_invalid")
        self.assertEqual(_fp(bad, condition_type="composite"), _fp(bad, condition_type="composite"))
