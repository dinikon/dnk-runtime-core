from src.modules.currency.application.directory.dto.currency_info_dto import (
    CurrencyInfoDTO,
)
from src.modules.currency.application.directory.query.list_currencies_query import (
    ListCurrenciesQuery,
)
from src.modules.currency.domain.directory.repository import CurrencyDirectory


class ListCurrenciesUseCase:
    """Execute the list currencies read scenario."""

    def __init__(self, repository: CurrencyDirectory):
        self.repository = repository

    async def __call__(self, query: ListCurrenciesQuery) -> list[CurrencyInfoDTO]:
        return [
            CurrencyInfoDTO.from_entity(info)
            for info in await self.repository.list_active()
        ]


__all__ = ["ListCurrenciesUseCase"]
