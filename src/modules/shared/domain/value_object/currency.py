from __future__ import annotations

from enum import StrEnum

from ..errors import DomainError


class CurrencyCodeNotSupportedError(DomainError):
    def __init__(self, value: str) -> None:
        super().__init__(f"currency code '{value}' is not supported")


class CurrencyCodeVO(StrEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    UAH = "UAH"
    PLN = "PLN"

    @classmethod
    def from_value(cls, value: str | CurrencyCodeVO) -> CurrencyCodeVO:
        if isinstance(value, cls):
            return value

        normalized = value.strip().upper()
        try:
            return cls(normalized)
        except ValueError:
            raise CurrencyCodeNotSupportedError(value) from None


__all__ = ["CurrencyCodeNotSupportedError", "CurrencyCodeVO"]
