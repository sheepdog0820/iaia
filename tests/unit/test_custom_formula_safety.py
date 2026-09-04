from types import SimpleNamespace

from django.test import SimpleTestCase

from accounts.utils.dice import calculate_custom_formula, validate_custom_formula


class CustomFormulaSafetyTests(SimpleTestCase):
    def setUp(self):
        self.character = SimpleNamespace(
            **{f"{name}_value": 60 for name in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")}
        )

    def test_rejects_unrecognized_text_and_python_expressions(self):
        for formula in (
            "EDU if 1 else STR",
            "EDU % 5",
            "EDU # ignored",
            "[EDU][0]",
            "EDU == STR",
            "EDU | STR",
            "EDU / 2 + STR ÷ 2",
            "1.5 + EDU",
            "1E2 + EDU",
            "2**3",
            "EDU ×× 2",
            "EDU 20",
            "EDU +",
            "(EDU",
            "EDU)",
            "()",
            "EDU(20)",
            "EDU + + STR",
            "STRSTR",
            "",
            " " * 201,
            "1+" * 100 + "1",
        ):
            with self.subTest(formula=formula):
                self.assertFalse(validate_custom_formula(formula))
                with self.assertRaises(ValueError):
                    calculate_custom_formula(self.character, formula)

    def test_arithmetic_precedence_grouping_and_rounding(self):
        for formula, expected in (
            ("EDU + STR × 2", 36),
            ("(EDU + STR) × 2", 48),
            ("EDU ÷ 5 × 3", 7),
            ("EDU - STR - 1", 0),
            ("-1 + EDU", 11),
            ("+EDU", 12),
            ("EDU + (-1)", 11),
            ("\t EDU + STR \n", 24),
            ("9" * 200, int("9" * 200)),
        ):
            with self.subTest(formula=formula):
                self.assertTrue(validate_custom_formula(formula))
                self.assertEqual(calculate_custom_formula(self.character, formula), expected)

    def test_division_by_zero_is_a_japanese_validation_error(self):
        self.assertTrue(validate_custom_formula("EDU ÷ (STR - 12)"))
        with self.assertRaisesRegex(ValueError, "ゼロ除算エラー"):
            calculate_custom_formula(self.character, "EDU ÷ (STR - 12)")

    def test_non_text_input_is_invalid(self):
        for formula in (None, 123, []):
            with self.subTest(formula=formula):
                self.assertFalse(validate_custom_formula(formula))
                with self.assertRaises(ValueError):
                    calculate_custom_formula(self.character, formula)
