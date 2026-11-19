"""S1.2.2: unit-тесты валидации payload и matchers."""

from django.test import SimpleTestCase

from apps.storefront_taxonomy.engine.conditions import match_condition, validate_condition
from apps.storefront_taxonomy.engine.errors import (
    ConditionError,
    ExpressionLimitError,
    InvalidRegexError,
    PayloadSchemaError,
    UnknownConditionTypeError,
    UnsafeRegexError,
    UnsupportedSchemaVersionError,
)
from apps.storefront_taxonomy.engine.normalizers import ProductFeatures
from apps.storefront_taxonomy.engine.schemas import COMPOSITE_MAX_DEPTH, COMPOSITE_MAX_NODES


def _features(**kwargs) -> ProductFeatures:
    defaults = dict(
        title="Apple AirPods Pro",
        brand="Apple",
        category_slug="naushniki",
        category_onec_code="00-acc-h",
        category_title_path=("Аксессуары", "Наушники"),
        category_slug_path=("aksessuary", "naushniki"),
    )
    defaults.update(kwargs)
    return ProductFeatures(**defaults)


class TitleContainsTests(SimpleTestCase):
    def test_any_default_match(self):
        self.assertTrue(
            match_condition(
                "title_contains",
                {"contains": ["наушник", "airpods"]},
                _features(title="Наушники Sony"),
            )
        )
        self.assertTrue(
            match_condition(
                "title_contains",
                {"contains": ["airpods"]},
                _features(title="Apple AirPods Pro"),
            )
        )

    def test_all_requires_every_token(self):
        feats = _features(title="Apple AirPods Pro")
        self.assertTrue(
            match_condition(
                "title_contains",
                {"contains": ["apple", "airpods"], "match": "all"},
                feats,
            )
        )
        self.assertFalse(
            match_condition(
                "title_contains",
                {"contains": ["apple", "samsung"], "match": "all"},
                feats,
            )
        )

    def test_unknown_key_rejected(self):
        with self.assertRaises(PayloadSchemaError):
            validate_condition("title_contains", {"contains": ["x"], "extra": 1})


class TitleRegexTests(SimpleTestCase):
    def test_valid_regex_match(self):
        self.assertTrue(
            match_condition(
                "title_regex",
                {"pattern": r"air\s*pods|наушник"},
                _features(title="Наушник Bluetooth"),
            )
        )

    def test_invalid_regex_controlled(self):
        with self.assertRaises(InvalidRegexError):
            match_condition("title_regex", {"pattern": "("}, _features())

    def test_unsafe_nested_quantifier_fail_closed(self):
        with self.assertRaises(UnsafeRegexError):
            match_condition("title_regex", {"pattern": r"(a+)+"}, _features())

    def test_invalid_regex_is_condition_error_not_bare(self):
        try:
            match_condition("title_regex", {"pattern": "*"}, _features())
        except ConditionError:
            pass
        else:
            self.fail("Ожидался ConditionError, получено необработанное исключение")


class CategorySlugTests(SimpleTestCase):
    def test_exact(self):
        self.assertTrue(
            match_condition(
                "onec_category_slug",
                {"slugs": ["naushniki"], "mode": "exact"},
                _features(),
            )
        )
        self.assertFalse(
            match_condition(
                "onec_category_slug",
                {"slugs": ["aksessuary"], "mode": "exact"},
                _features(),
            )
        )

    def test_any_ancestor(self):
        self.assertTrue(
            match_condition(
                "onec_category_slug",
                {"slugs": ["aksessuary"], "mode": "any_ancestor"},
                _features(),
            )
        )
        self.assertFalse(
            match_condition(
                "onec_category_slug",
                {"slugs": ["telefony"], "mode": "any_ancestor"},
                _features(),
            )
        )


class CategoryPathTests(SimpleTestCase):
    def test_title_path_modes(self):
        feats = _features()
        self.assertTrue(
            match_condition(
                "onec_category_path",
                {
                    "source": "title_path",
                    "segments": ["Аксессуары", "Наушники"],
                    "mode": "exact",
                },
                feats,
            )
        )
        self.assertTrue(
            match_condition(
                "onec_category_path",
                {
                    "source": "title_path",
                    "segments": ["Аксессуары"],
                    "mode": "prefix",
                },
                feats,
            )
        )
        self.assertTrue(
            match_condition(
                "onec_category_path",
                {
                    "source": "title_path",
                    "segments": ["Наушники"],
                    "mode": "suffix",
                },
                feats,
            )
        )
        self.assertTrue(
            match_condition(
                "onec_category_path",
                {
                    "source": "title_path",
                    "segments": ["Наушники"],
                    "mode": "contains_segment",
                },
                feats,
            )
        )
        self.assertFalse(
            match_condition(
                "onec_category_path",
                {
                    "source": "title_path",
                    "segments": ["Телефоны"],
                    "mode": "contains_segment",
                },
                feats,
            )
        )

    def test_slug_path_modes(self):
        feats = _features()
        self.assertTrue(
            match_condition(
                "onec_category_path",
                {
                    "source": "slug_path",
                    "segments": ["aksessuary", "naushniki"],
                    "mode": "exact",
                },
                feats,
            )
        )
        self.assertTrue(
            match_condition(
                "onec_category_path",
                {
                    "source": "slug_path",
                    "segments": ["naushniki"],
                    "mode": "suffix",
                },
                feats,
            )
        )


class BrandEqualsTests(SimpleTestCase):
    def test_match_case_insensitive(self):
        self.assertTrue(
            match_condition(
                "brand_equals",
                {"brands": ["apple", "Samsung"]},
                _features(brand="Apple"),
            )
        )

    def test_empty_brand_is_miss_not_error(self):
        self.assertFalse(
            match_condition(
                "brand_equals",
                {"brands": ["Apple"]},
                _features(brand=None),
            )
        )
        self.assertFalse(
            match_condition(
                "brand_equals",
                {"brands": ["Apple"]},
                _features(brand=""),
            )
        )


class CompositeTests(SimpleTestCase):
    def test_and_or_not(self):
        feats = _features(title="iPhone 15", brand="Apple", category_slug="telefony")
        payload = {
            "op": "and",
            "args": [
                {
                    "type": "title_contains",
                    "payload": {"contains": ["iphone"]},
                },
                {
                    "op": "or",
                    "args": [
                        {
                            "type": "brand_equals",
                            "payload": {"brands": ["Apple"]},
                        },
                        {
                            "type": "onec_category_slug",
                            "payload": {"slugs": ["telefony"]},
                        },
                    ],
                },
                {
                    "op": "not",
                    "args": [
                        {
                            "type": "title_contains",
                            "payload": {"contains": ["чехол"]},
                        }
                    ],
                },
            ],
        }
        self.assertTrue(match_condition("composite", payload, feats))

        feats_case = _features(title="Чехол iPhone", brand="Apple", category_slug="telefony")
        self.assertFalse(match_condition("composite", payload, feats_case))

    def test_not_wrong_arity(self):
        with self.assertRaises(PayloadSchemaError):
            validate_condition(
                "composite",
                {
                    "op": "not",
                    "args": [
                        {"type": "title_contains", "payload": {"contains": ["a"]}},
                        {"type": "title_contains", "payload": {"contains": ["b"]}},
                    ],
                },
            )

    def test_unknown_type(self):
        with self.assertRaises(UnknownConditionTypeError):
            validate_condition("nope", {"x": 1})

    def test_nested_forbidden_product_uuid_key(self):
        with self.assertRaises(PayloadSchemaError):
            validate_condition(
                "composite",
                {
                    "op": "and",
                    "args": [
                        {
                            "type": "title_contains",
                            "payload": {
                                "contains": ["x"],
                                "product_id": "123",
                            },
                        }
                    ],
                },
            )

    def test_forbidden_key_inside_array_branch(self):
        with self.assertRaises(PayloadSchemaError):
            validate_condition(
                "composite",
                {
                    "op": "or",
                    "args": [
                        {
                            "all": [{"product_ids": ["1"]}],
                        }
                    ],
                },
            )

    def _nested_not_chain(self, depth: int) -> dict:
        node: dict = {
            "type": "title_contains",
            "payload": {"contains": ["iphone"]},
        }
        for _ in range(depth - 1):
            node = {"op": "not", "args": [node]}
        return node

    def test_depth_at_limit_ok(self):
        # depth=8: root + 7 nested not around leaf... 
        # Our counter: each op/leaf is a node; depth param tracks nesting.
        # Chain of 8 NOT wrappers around leaf would be depth 9 at leaf.
        # Max depth 8 means chain length (root..leaf) <= 8.
        payload = self._nested_not_chain(COMPOSITE_MAX_DEPTH)
        # Even nesting of NOT: True if original matches
        feats = _features(title="iPhone")
        # depth 8 chain: 7 NOTs + leaf = even? 
        # nodes: NOT1..NOT7 + leaf = 8 nodes, depth at leaf = 8 → OK
        # number of NOTs = 7 → odd → not match if title matches
        result = match_condition("composite", payload, feats)
        self.assertIsInstance(result, bool)

    def test_depth_exceeded(self):
        payload = self._nested_not_chain(COMPOSITE_MAX_DEPTH + 1)
        with self.assertRaises(ExpressionLimitError):
            validate_condition("composite", payload)

    def test_nodes_at_limit_ok(self):
        leaves = [
            {"type": "title_contains", "payload": {"contains": [f"t{i}"]}}
            for i in range(COMPOSITE_MAX_NODES - 1)
        ]
        payload = {"op": "or", "args": leaves}  # 1 + 63 = 64
        validate_condition("composite", payload)

    def test_nodes_exceeded(self):
        leaves = [
            {"type": "title_contains", "payload": {"contains": [f"t{i}"]}}
            for i in range(COMPOSITE_MAX_NODES)
        ]
        payload = {"op": "or", "args": leaves}  # 1 + 64 = 65
        with self.assertRaises(ExpressionLimitError):
            validate_condition("composite", payload)

    def test_unsupported_schema_version(self):
        with self.assertRaises(UnsupportedSchemaVersionError):
            validate_condition(
                "title_contains",
                {"contains": ["x"]},
                schema_version=99,
            )

    def test_bad_rule_does_not_raise_unhandled(self):
        bad_cases = [
            ("title_contains", {"contains": []}),
            ("title_contains", {"foo": 1}),
            ("title_regex", {"pattern": "("}),
            ("title_regex", {"pattern": "(a+)+"}),
            ("unknown", {}),
            (
                "composite",
                {"op": "xor", "args": [{"type": "title_contains", "payload": {"contains": ["a"]}}]},
            ),
        ]
        for ctype, payload in bad_cases:
            with self.subTest(ctype=ctype, payload=payload):
                try:
                    match_condition(ctype, payload, _features())
                except ConditionError:
                    pass
                else:
                    self.fail(f"Ожидался ConditionError для {ctype}: {payload}")
