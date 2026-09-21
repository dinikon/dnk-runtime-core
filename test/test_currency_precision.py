from decimal import Decimal, Context, Inexact, localcontext
import unittest

from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.money import Money
from src.modules.shared.domain.value_object.money_errors import (
    InexactMoneyDivisionError,
    InvalidMoneyError,
)
from src.modules.currency.domain.conversion.quantizer import MoneyQuantizer
from src.modules.currency.domain.conversion.value_object.conversion_purpose import (
    ConversionPurpose,
)
from src.modules.currency.domain.policy.value_object.rounding_mode import RoundingMode
from src.modules.currency.domain.conversion.error import CurrencyPrecisionUndefined


class ExactMoneyTests(unittest.TestCase):
    def test_division_is_independent_of_context_and_preserves_large_values(self):
        values = [
            ("12345678901234567890123456789", "1", "12345678901234567890123456789"),
            ("123.45", "2", "61.725"),
            ("1", "0.125", "8"),
            ("-3", "-8", "0.375"),
            ("0", "3", "0"),
            ("1", "100000000000000000000000000000000", "1E-32"),
        ]
        with localcontext(Context(prec=3)) as context:
            context.traps[Inexact] = True
            for amount, divisor, expected in values:
                with self.subTest(amount=amount, divisor=divisor):
                    self.assertEqual(
                        (
                            Money(Decimal(amount), CurrencyCodeVO("USD"))
                            / Decimal(divisor)
                        ).amount,
                        Decimal(expected),
                    )

    def test_repeating_result_requires_explicit_precision(self):
        value = Money(Decimal("1"), CurrencyCodeVO("USD"))
        with self.assertRaises(InexactMoneyDivisionError):
            value / 3
        with localcontext(Context(prec=2)) as context:
            context.traps[Inexact] = True
            self.assertEqual(
                value.divide(3, precision=8, rounding="ROUND_HALF_UP").amount,
                Decimal("0.33333333"),
            )
        for scalar in (0.5, True, Decimal("NaN")):
            with self.assertRaises(InvalidMoneyError):
                value / scalar

    def test_purpose_precision_and_missing_minor_units(self):
        q = MoneyQuantizer()
        for code, digits, expected in [
            ("JPY", 0, "2"),
            ("UAH", 2, "1.56"),
            ("KWD", 3, "1.555"),
        ]:
            value = Money(Decimal("1.555"), CurrencyCodeVO(code))
            self.assertEqual(
                q.quantize(
                    value,
                    minor_units=digits,
                    rounding_mode=RoundingMode.HALF_UP,
                    purpose=ConversionPurpose.DISPLAY,
                ).amount,
                Decimal(expected),
            )
        value = Money(Decimal("1.234567"), CurrencyCodeVO("XAU"))
        self.assertEqual(
            q.quantize(
                value,
                minor_units=None,
                rounding_mode=RoundingMode.HALF_UP,
                purpose=ConversionPurpose.DISPLAY,
            ),
            value,
        )
        self.assertEqual(
            q.quantize(
                value,
                minor_units=2,
                rounding_mode=RoundingMode.HALF_UP,
                purpose=ConversionPurpose.CALCULATION,
            ),
            value,
        )
        with self.assertRaises(CurrencyPrecisionUndefined):
            q.quantize(
                value,
                minor_units=None,
                rounding_mode=RoundingMode.HALF_UP,
                purpose=ConversionPurpose.BOOKING,
            )
        self.assertEqual(
            q.quantize(
                value,
                minor_units=None,
                precision=4,
                rounding_mode=RoundingMode.HALF_UP,
                purpose=ConversionPurpose.BOOKING,
            ).amount,
            Decimal("1.2346"),
        )
        self.assertEqual(
            q.quantize(
                value,
                minor_units=None,
                precision=12,
                rounding_mode=RoundingMode.HALF_UP,
                purpose=ConversionPurpose.BOOKING,
            ).amount,
            Decimal("1.234567000000"),
        )
        for invalid in (-1, True):
            with self.assertRaises(CurrencyPrecisionUndefined):
                q.quantize(
                    value,
                    minor_units=2,
                    precision=invalid,
                    rounding_mode=RoundingMode.HALF_UP,
                    purpose=ConversionPurpose.CALCULATION,
                )

    def test_arithmetic_and_quantization_ignore_ambient_traps_and_exponent_limits(self):
        from decimal import Inexact, Rounded, localcontext, ROUND_DOWN
        from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
        from src.modules.currency.domain.conversion.quantizer import MoneyQuantizer
        from src.modules.currency.domain.conversion.value_object.conversion_purpose import (
            ConversionPurpose,
        )
        from src.modules.currency.domain.policy.value_object.rounding_mode import (
            RoundingMode,
        )

        with localcontext() as context:
            context.prec = 1
            context.Emax = 2
            context.Emin = -2
            context.rounding = ROUND_DOWN
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            a = Money(Decimal("123456.789"), CurrencyCodeVO("UAH"))
            self.assertEqual((a + a).amount, Decimal("246913.578"))
            self.assertEqual((a * Decimal("1000")).amount, Decimal("123456789"))
            self.assertEqual((a / Decimal("1000")).amount, Decimal("123.456789"))
            self.assertEqual(
                MoneyQuantizer()
                .quantize(
                    a,
                    minor_units=2,
                    rounding_mode=RoundingMode.HALF_UP,
                    purpose=ConversionPurpose.BOOKING,
                )
                .amount,
                Decimal("123456.79"),
            )
