from __future__ import annotations

from dataclasses import dataclass
import re

from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)


@dataclass(frozen=True, slots=True)
class CurrencyVO:
    """Неизменяемый код валюты; наличие в справочнике проверяет Application."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует трёхбуквенный ASCII-код без проверки внешнего справочника."""
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Za-z]{3}", self.value.strip()
        ):
            raise CurrencyCodeNotSupportedError(str(self.value))
        object.__setattr__(self, "value", self.value.strip().upper())

    @classmethod
    def from_value(cls, value: str | CurrencyVO) -> CurrencyVO:
        """Создаёт валюту из строки или возвращает готовый VO."""
        if isinstance(value, cls):
            return value

        return cls(value)

    def __str__(self) -> str:
        """Возвращает нормализованный код валюты."""
        return self.value


# Совместимость существующего имени без второй реализации валюты.
CurrencyCodeVO = CurrencyVO
