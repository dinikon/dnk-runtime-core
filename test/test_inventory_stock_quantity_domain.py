"""Точное применение дельты к физическому количеству без округления."""

import unittest
from decimal import (
    Decimal,
    Inexact,
    MAX_EMAX,
    MIN_EMIN,
    ROUND_DOWN,
    Rounded,
    localcontext,
)
from fractions import Fraction

from src.modules.inventory.domain.error import (
    InvalidQuantityError,
    InvalidQuantityRulesError,
    InvalidStockDeltaError,
    NegativeStockQuantityError,
    QuantityStepError,
    StockQuantityArithmeticError,
)
from src.modules.inventory.domain.policy.stock_quantity import StockQuantityPolicy
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


class StockQuantityPolicyTests(unittest.TestCase):
    """Проверяет арифметику отдельно от измерений, версий и разрешения операций."""

    def apply(self, quantity: str, delta: str, step: str = "0.01") -> QuantityVO:
        """Применяет явно заданные десятичные значения через типизированную Policy."""
        return StockQuantityPolicy.apply_delta(
            quantity=QuantityVO(Decimal(quantity)),
            delta=StockDeltaVO(Decimal(delta)),
            rules=QuantityRulesVO(Decimal(step)),
        )

    def test_addition_subtraction_and_trailing_zeros_are_exact(self) -> None:
        """Принимает положительную, отрицательную и нулевую дельту с точной кратностью."""
        for quantity, delta, step, expected in (
            ("0", "5", "1", "5"),
            ("10", "-5", "1", "5"),
            ("1.2500", "0.0500", "0.05", "1.30"),
            ("1.25", "-1.25", "0.05", "0"),
            ("0", "0", "1", "0"),
            ("1.25", "-0.000", "0.05", "1.25"),
            ("0", "0.000000001", "0.000000001", "0.000000001"),
        ):
            with self.subTest(quantity=quantity, delta=delta):
                self.assertEqual(
                    self.apply(quantity, delta, step).value, Decimal(expected)
                )
        original = QuantityVO(Decimal("1.2500"))
        self.assertIs(
            StockQuantityPolicy.apply_delta(
                quantity=original,
                delta=StockDeltaVO(Decimal("-0.000")),
                rules=QuantityRulesVO(Decimal("0.05")),
            ),
            original,
        )

    def test_negative_result_is_rejected(self) -> None:
        """Недостаток физического количества не превращается в отрицательное значение или ноль."""
        for quantity, delta in (("0", "-1"), ("1", "-2"), ("0.01", "-0.02")):
            with (
                self.subTest(quantity=quantity, delta=delta),
                self.assertRaises(NegativeStockQuantityError),
            ):
                self.apply(quantity, delta)

    def test_current_quantity_and_delta_must_match_step(self) -> None:
        """Некратный исходный остаток не исправляется скрытым округлением или встречной дельтой."""
        for quantity, delta in (
            ("1.23", "0"),
            ("1.23", "0.02"),
            ("1.25", "0.03"),
            ("0", "-0.001"),
        ):
            with (
                self.subTest(quantity=quantity, delta=delta),
                self.assertRaises(QuantityStepError),
            ):
                self.apply(quantity, delta, "0.05")

    def test_results_match_independent_rational_arithmetic(self) -> None:
        """Сравнивает разные знаки и исходные остатки с точной рациональной суммой."""
        for quantity in ("0", "0.01", "1.25", "100.00"):
            for delta in ("-100", "-1.25", "-0.01", "0", "0.01", "1.25", "100"):
                expected = Fraction(Decimal(quantity)) + Fraction(Decimal(delta))
                with self.subTest(quantity=quantity, delta=delta):
                    if expected < 0:
                        with self.assertRaises(NegativeStockQuantityError):
                            self.apply(quantity, delta)
                    else:
                        self.assertEqual(
                            Fraction(self.apply(quantity, delta).value), expected
                        )

    def test_hostile_decimal_context_does_not_round_result_or_set_flags(self) -> None:
        """Точность, границы порядка и traps вызывающего кода не влияют на расчёт."""
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.rounding = ROUND_DOWN
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            result = self.apply("12345678901234567890.12345", "-0.00345", "0.00001")
            self.assertEqual(result.value, Decimal("12345678901234567890.12000"))
            self.assertEqual(self.apply("0.95", "0.10", "0.05").value, Decimal("1.05"))
            self.assertEqual(
                self.apply("1E100", "1", "1").value, Decimal("1" + "0" * 99 + "1")
            )
            self.assertFalse(any(context.flags.values()))

    def test_extreme_exponents_are_exact_or_raise_controlled_arithmetic_error(
        self,
    ) -> None:
        """Сохраняет точные крайние значения и отказывает вместо огромного разворачивания или Infinity."""
        huge = Decimal((0, (1,), MAX_EMAX))
        rules = QuantityRulesVO(Decimal(1))
        self.assertEqual(
            StockQuantityPolicy.apply_delta(
                quantity=QuantityVO(huge), delta=StockDeltaVO(huge), rules=rules
            ).value,
            Decimal((0, (2,), MAX_EMAX)),
        )
        self.assertTrue(
            StockQuantityPolicy.apply_delta(
                quantity=QuantityVO(huge),
                delta=StockDeltaVO(huge.copy_negate()),
                rules=rules,
            ).value.is_zero()
        )
        tiny = Decimal((0, (1,), MIN_EMIN))
        self.assertEqual(
            StockQuantityPolicy.apply_delta(
                quantity=QuantityVO(tiny),
                delta=StockDeltaVO(tiny),
                rules=QuantityRulesVO(tiny),
            ).value,
            Decimal((0, (2,), MIN_EMIN)),
        )
        with self.assertRaises(StockQuantityArithmeticError):
            StockQuantityPolicy.apply_delta(
                quantity=QuantityVO(huge), delta=StockDeltaVO(Decimal(1)), rules=rules
            )
        maximum = Decimal((0, (9,), MAX_EMAX))
        with self.assertRaises(StockQuantityArithmeticError):
            StockQuantityPolicy.apply_delta(
                quantity=QuantityVO(maximum), delta=StockDeltaVO(maximum), rules=rules
            )

    def test_policy_requires_typed_values(self) -> None:
        """Сырые числа и настройки отклоняются доменными ошибками."""
        values = dict(
            quantity=QuantityVO(Decimal(1)),
            delta=StockDeltaVO(Decimal(1)),
            rules=QuantityRulesVO(Decimal(1)),
        )
        for changes, error in (
            (dict(quantity=Decimal(1)), InvalidQuantityError),
            (dict(delta=Decimal(1)), InvalidStockDeltaError),
            (dict(rules=None), InvalidQuantityRulesError),
        ):
            with self.subTest(changes=changes), self.assertRaises(error):
                StockQuantityPolicy.apply_delta(**(values | changes))
