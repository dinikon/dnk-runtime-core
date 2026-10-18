from src.modules.currency.application.port.catalog import ExchangeRateCurrencyDTO
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.handler import (
    GetCurrencyValidationCatalogHandler,
)
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.query import (
    GetCurrencyValidationCatalogQuery,
)


class ReferenceDataExchangeRateCurrencyCatalog:
    """Переводит публичный Application-контракт Reference Data в порт Currency."""

    def __init__(self, handler: GetCurrencyValidationCatalogHandler) -> None:
        """Принимает публичный batch-сценарий без доступа к чужим SQL-моделям."""
        self._handler = handler

    async def get_active(
        self, codes: tuple[str, ...]
    ) -> tuple[ExchangeRateCurrencyDTO, ...]:
        """Проверяет коды через контракт и возвращает собственные DTO адаптера."""
        result = await self._handler.execute(GetCurrencyValidationCatalogQuery(codes))
        return tuple(
            ExchangeRateCurrencyDTO(item.code, item.numeric_code, item.is_metal)
            for item in result.currencies
        )
