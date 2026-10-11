from collections.abc import Mapping
from typing import Any

from src.modules.reference_data.application.currency.query.validate_currency.dto import (
    ValidateCurrencyResultDTO,
)


class CurrencyQueryMapper:
    """Преобразует SQL-проекцию активной валюты в DTO проверки."""

    @staticmethod
    def to_validation(row: Mapping[str, Any]) -> ValidateCurrencyResultDTO:
        """Собирает результат проверки без I/O и бизнес-правил."""
        return ValidateCurrencyResultDTO(
            code=row["code"],
            numeric_code=row["numeric_code"],
            minor_units=row["minor_units"],
        )
