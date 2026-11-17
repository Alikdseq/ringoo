"""RELEASE 46.1 Stage A: numeric text normalization for 1C price/quantity."""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase

from integrations.onec.parser import (
    MONEY_QUANT,
    OneCProductRow,
    _normalize_numeric_text,
)


def _row(*, price: str = "", quantity: str = "") -> OneCProductRow:
    return OneCProductRow(
        code="00-00000001",
        parent_code="",
        name="t",
        type_name="",
        type_id="",
        sklad="",
        sklad_id="",
        series="",
        series_id="",
        quantity_raw=quantity,
        price_raw=price,
    )


class NormalizeNumericTextTests(SimpleTestCase):
    def test_regular_space_thousands(self):
        self.assertEqual(_normalize_numeric_text("36 990,00"), "36990.00")
        self.assertEqual(_normalize_numeric_text("36 990.00"), "36990.00")

    def test_nbsp(self):
        self.assertEqual(_normalize_numeric_text("36\u00a0990,00"), "36990.00")
        self.assertEqual(_normalize_numeric_text("36\u00a0990.00"), "36990.00")

    def test_narrow_nbsp(self):
        self.assertEqual(_normalize_numeric_text("36\u202f990,00"), "36990.00")
        self.assertEqual(_normalize_numeric_text("36\u202f990.00"), "36990.00")

    def test_figure_space(self):
        self.assertEqual(_normalize_numeric_text("36\u2007990,00"), "36990.00")

    def test_thin_space(self):
        self.assertEqual(_normalize_numeric_text("36\u2009990,00"), "36990.00")

    def test_dot_decimal(self):
        self.assertEqual(_normalize_numeric_text("36990.00"), "36990.00")
        self.assertEqual(_normalize_numeric_text("36.99"), "36.99")

    def test_comma_decimal(self):
        self.assertEqual(_normalize_numeric_text("36,99"), "36.99")
        self.assertEqual(_normalize_numeric_text("36990,00"), "36990.00")

    def test_both_separators_us_then_eu(self):
        self.assertEqual(_normalize_numeric_text("36,990.00"), "36990.00")
        self.assertEqual(_normalize_numeric_text("36.990,00"), "36990.00")

    def test_correct_thousand_grouping_repeated_sep(self):
        self.assertEqual(_normalize_numeric_text("1.000.000"), "1000000")
        self.assertEqual(_normalize_numeric_text("1.000.000,50"), "1000000.50")

    def test_incorrect_thousand_grouping(self):
        with self.assertRaises(ValueError):
            _normalize_numeric_text("36,99,00")
        with self.assertRaises(ValueError):
            _normalize_numeric_text("1.0.00")

    def test_multiple_decimal_separators(self):
        with self.assertRaises(ValueError):
            _normalize_numeric_text("36..990")
        with self.assertRaises(ValueError):
            _normalize_numeric_text("36,,99")

    def test_foreign_characters(self):
        with self.assertRaises(ValueError):
            _normalize_numeric_text("abc")
        with self.assertRaises(ValueError):
            _normalize_numeric_text("36_990.00")
        with self.assertRaises(ValueError):
            _normalize_numeric_text("36’990.00")

    def test_empty_string(self):
        self.assertEqual(_normalize_numeric_text(""), "")
        self.assertEqual(_normalize_numeric_text("   "), "")
        self.assertEqual(_normalize_numeric_text(None), "")

    def test_tab_rejected(self):
        with self.assertRaises(ValueError):
            _normalize_numeric_text("36\t990.00")


class ParsePriceTests(SimpleTestCase):
    def test_space_variants_parse_to_decimal(self):
        cases = [
            "36 990.00",
            "36\u00a0990.00",
            "36\u202f990.00",
            "36\u2007990.00",
            "36\u2009990.00",
            "36 990,00",
            "36,990.00",
            "36.990,00",
            "36,99",
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                value = _row(price=raw).parse_price()
                self.assertIsInstance(value, Decimal)
                self.assertNotIsInstance(value, float)

    def test_fixture_like_nbsp_price(self):
        value = _row(price="36\u00a0990.00").parse_price()
        self.assertEqual(value, Decimal("36990.00"))
        self.assertIsNone(_row(price="36\u00a0990.00").price_problem())

    def test_empty_price_is_none_not_zero(self):
        row = _row(price="")
        self.assertIsNone(row.parse_price())
        self.assertEqual(row.price_problem(), "empty")
        self.assertNotEqual(row.parse_price(), Decimal("0"))

    def test_invalid_price_none_and_problem(self):
        row = _row(price="abc")
        self.assertIsNone(row.parse_price())
        self.assertEqual(row.price_problem(), "not_a_number")

    def test_ambiguous_multi_comma_rejected(self):
        row = _row(price="36,99,00")
        self.assertIsNone(row.parse_price())
        self.assertEqual(row.price_problem(), "not_a_number")

    def test_double_dot_rejected(self):
        row = _row(price="36..990")
        self.assertIsNone(row.parse_price())
        self.assertEqual(row.price_problem(), "not_a_number")

    def test_price_precision_limit_unchanged(self):
        # Existing business rule: more than 2 decimal places → precision problem.
        row = _row(price="10.001")
        self.assertEqual(row.parse_price(), Decimal("10.001"))
        self.assertEqual(row.price_problem(), "precision")
        self.assertEqual(MONEY_QUANT, Decimal("0.01"))

    def test_empty_does_not_become_zero_via_problem_path(self):
        row = _row(price="")
        self.assertIsNone(row.parse_price())
        self.assertEqual(row.price_problem(), "empty")


class ParseQuantityTests(SimpleTestCase):
    def test_empty_quantity_none_not_zero(self):
        row = _row(quantity="")
        self.assertIsNone(row.parse_quantity())
        self.assertEqual(row.quantity_problem(), "empty")

    def test_onec_fractional_integer_quantity(self):
        # Fixture contract: quantity="1.000" / "72.000"
        row = _row(quantity="1.000")
        self.assertEqual(row.parse_quantity(), Decimal("1.000"))
        self.assertIsNone(row.quantity_problem())
        row72 = _row(quantity="72.000")
        self.assertEqual(row72.parse_quantity(), Decimal("72.000"))
        self.assertIsNone(row72.quantity_problem())

    def test_invalid_quantity(self):
        row = _row(quantity="12.5")
        self.assertEqual(row.parse_quantity(), Decimal("12.5"))
        self.assertEqual(row.quantity_problem(), "not_integer")
        bad = _row(quantity="x")
        self.assertIsNone(bad.parse_quantity())
        self.assertEqual(bad.quantity_problem(), "not_a_number")

    def test_quantity_with_unicode_spaces(self):
        row = _row(quantity="1\u202f000")
        self.assertEqual(row.parse_quantity(), Decimal("1000"))
        self.assertIsNone(row.quantity_problem())

    def test_no_float_in_quantity(self):
        value = _row(quantity="2.000").parse_quantity()
        self.assertIsInstance(value, Decimal)
        self.assertNotIsInstance(value, float)
