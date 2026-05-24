from __future__ import annotations

from enum import StrEnum

from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)


class CurrencyCodeVO(StrEnum):
    """Value object поддержанного ISO-like кода валюты."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    UAH = "UAH"
    PLN = "PLN"

    @classmethod
    def from_value(cls, value: str | CurrencyCodeVO) -> CurrencyCodeVO:
        """Создает CurrencyCodeVO из строки или возвращает готовый enum."""
        if isinstance(value, cls):
            return value

        normalized = value.strip().upper()
        try:
            return cls(normalized)
        except ValueError:
            raise CurrencyCodeNotSupportedError(value) from None


__all__ = ["CurrencyCodeNotSupportedError", "CurrencyCodeVO"]
