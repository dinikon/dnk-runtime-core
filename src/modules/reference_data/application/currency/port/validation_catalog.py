from typing import Protocol
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.dto import (
    GetCurrencyValidationCatalogRecordDTO,
)


class CurrencyValidationCatalogQueryRepositoryProtocol(Protocol):
    """Читает batch-проекцию активных валют без загрузки доменных записей."""

    async def get_active_codes(
        self, codes: tuple[str, ...]
    ) -> tuple[GetCurrencyValidationCatalogRecordDTO, ...]:
        """Возвращает активные записи запрошенного набора кодов."""
        ...
