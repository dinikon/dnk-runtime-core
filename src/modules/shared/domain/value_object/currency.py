from __future__ import annotations

from enum import StrEnum

from ..errors import DomainError


class CurrencyCodeNotSupportedError(DomainError):
    """Ошибка неподдержанного кода валюты."""

    def __init__(self, value: str) -> None:
        """Формирует сообщение с неподдержанным кодом валюты."""
        super().__init__(f"currency code '{value}' is not supported")


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
