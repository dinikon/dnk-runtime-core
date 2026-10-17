from collections.abc import Mapping
from typing import Any
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.dto import (
    GetCurrencyValidationCatalogRecordDTO,
)


class CurrencyValidationCatalogQueryMapper:
    """Преобразует batch-проекцию в контракт проверки валют."""

    @staticmethod
    def to_validation_item(
        row: Mapping[str, Any],
    ) -> GetCurrencyValidationCatalogRecordDTO:
        """Отображает поля SQL без классификации и бизнес-правил."""
        return GetCurrencyValidationCatalogRecordDTO(
            row["code"], row["numeric_code"], row["minor_units"]
        )
