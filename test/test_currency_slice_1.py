"""Денежные VO и проверка валют через Reference Data."""

from dataclasses import FrozenInstanceError
from decimal import Decimal, Inexact, localcontext
import unittest
from unittest.mock import AsyncMock
from src.modules.reference_data.application.currency.query.validate_currency.dto import (
    ValidateCurrencyResultDTO,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO, CurrencyVO
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.shared.domain.value_object.money_error import (
    InvalidMoneyError,
    MoneyCurrencyMismatchError,
)


class MoneyValueObjectTests(unittest.TestCase):
    def test_currency_normalization_identity_and_legacy_import(self) -> None:
        currency = CurrencyVO.from_value(" jpy ")
        self.assertEqual(currency.value, "JPY")
        self.assertEqual(str(currency), "JPY")
        self.assertIs(CurrencyVO.from_value(currency), currency)
        self.assertIs(CurrencyCodeVO, CurrencyVO)
        from src.modules.shared import CurrencyCodeVO as LegacyCurrency

        self.assertEqual(LegacyCurrency.from_value("jpy"), currency)
        with self.assertRaises(FrozenInstanceError):
            currency.value = "USD"

    def test_invalid_currency_shape_is_domain_error(self) -> None:
        for value in (None, 123, "US", "USDD", "U1D", "€UR", "ßD", ""):
            with (
                self.subTest(value=value),
                self.assertRaises(CurrencyCodeNotSupportedError),
            ):
                CurrencyVO.from_value(value)

    def test_signed_money_rounding_and_ambient_context_independence(self) -> None:
        usd = CurrencyVO("USD")
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            positive = MoneyVO(Decimal("12345.23455"), usd)
            negative = MoneyVO(Decimal("-12345.23455"), usd)
            self.assertEqual(positive.amount, Decimal("12345.2346"))
            self.assertEqual(negative.amount, Decimal("-12345.2346"))
            self.assertEqual((positive + negative).amount, Decimal("0.0000"))
            self.assertEqual(
                (positive - MoneyVO(Decimal("20000"), usd)).amount,
                Decimal("-7654.7654"),
            )
        self.assertFalse(MoneyVO(Decimal("-0.00001"), usd).amount.is_signed())
        with self.assertRaises(FrozenInstanceError):
            positive.amount = Decimal("1")

    def test_money_rejects_invalid_input_and_overflow_after_rounding(self) -> None:
        usd = CurrencyVO("USD")
        for amount in (
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            Decimal("1000000000000000"),
            Decimal("-1000000000000000"),
            Decimal("999999999999999.99995"),
            Decimal("-999999999999999.99995"),
            1.5,
            "1",
            True,
        ):
            with self.subTest(amount=amount), self.assertRaises(InvalidMoneyError):
                MoneyVO(amount, usd)
        with self.assertRaises(InvalidMoneyError):
            MoneyVO(Decimal("1"), "USD")
        maximum = MoneyVO(Decimal("999999999999999.9999"), usd)
        with self.assertRaises(InvalidMoneyError):
            maximum + MoneyVO(Decimal("0.0001"), usd)
        with self.assertRaises(InvalidMoneyError):
            maximum - MoneyVO(Decimal("-0.0001"), usd)

    def test_money_rejects_arithmetic_across_currencies(self) -> None:
        usd = MoneyVO(Decimal("1"), CurrencyVO("USD"))
        uah = MoneyVO(Decimal("1"), CurrencyVO("UAH"))
        with self.assertRaises(MoneyCurrencyMismatchError):
            usd + uah
        with self.assertRaises(MoneyCurrencyMismatchError):
            usd - uah


class CurrencyApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_validate_currency_normalizes_and_returns_own_dto(self) -> None:
        dto = ValidateCurrencyResultDTO("JPY", "392", 0)
        repository = AsyncMock()
        repository.get_active.return_value = dto
        result = await ValidateCurrencyHandler(repository).execute(
            ValidateCurrencyQuery(" jpy ")
        )
        self.assertEqual(result, dto)
        repository.get_active.assert_awaited_once_with("JPY")

    async def test_validate_currency_rejects_missing_or_inactive(self) -> None:
        repository = AsyncMock()
        repository.get_active.return_value = None
        with self.assertRaises(CurrencyCodeNotSupportedError):
            await ValidateCurrencyHandler(repository).execute(
                ValidateCurrencyQuery("ZZZ")
            )
        repository.get_active.reset_mock()
        with self.assertRaises(CurrencyCodeNotSupportedError):
            await ValidateCurrencyHandler(repository).execute(
                ValidateCurrencyQuery("US")
            )
        repository.get_active.assert_not_awaited()
