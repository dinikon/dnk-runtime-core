from src.modules.reference_data.domain.currency.policy import CurrencyMetalPolicy
from src.modules.reference_data.application.currency.port.validation_catalog import (
    CurrencyValidationCatalogQueryRepositoryProtocol,
)
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.query import (
    GetCurrencyValidationCatalogQuery,
)
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.dto import (
    GetCurrencyValidationCatalogResultDTO,
    GetCurrencyValidationCatalogItemDTO,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO


class GetCurrencyValidationCatalogHandler:
    """Проверяет набор кодов через специализированный порт проекций."""

    def __init__(
        self, repository: CurrencyValidationCatalogQueryRepositoryProtocol
    ) -> None:
        """Принимает query repository внешнего UoW."""
        self._repository = repository

    async def execute(
        self, query: GetCurrencyValidationCatalogQuery
    ) -> GetCurrencyValidationCatalogResultDTO:
        """Нормализует коды и возвращает свой DTO с найденными и отсутствующими."""
        codes = tuple(sorted({CurrencyVO(code).value for code in query.codes}))
        records = await self._repository.get_active_codes(codes)
        found = {item.code for item in records}
        return GetCurrencyValidationCatalogResultDTO(
            tuple(
                GetCurrencyValidationCatalogItemDTO(
                    item.code,
                    item.numeric_code,
                    item.minor_units,
                    CurrencyMetalPolicy.is_metal(item.code),
                )
                for item in records
            ),
            tuple(code for code in codes if code not in found),
        )
