from src.modules.crm.application.deal.port.currency_catalog import (
    DealCurrencyCatalogPort,
)
from src.modules.crm.application.deal.query.list_deal_currencies.query import (
    ListDealCurrenciesQuery,
)
from src.modules.crm.application.deal.query.list_deal_currencies.dto import (
    ListDealCurrenciesResultDTO,
    DealCurrencyItemDTO,
)


class ListDealCurrenciesHandler:
    """Читает заменяемую политику валют продаж."""

    def __init__(self, catalog: DealCurrencyCatalogPort) -> None:
        """Принимает абстрактный справочник."""
        self._catalog = catalog

    async def execute(
        self, query: ListDealCurrenciesQuery
    ) -> ListDealCurrenciesResultDTO:
        """Возвращает конкретный справочник без записи."""
        return ListDealCurrenciesResultDTO(
            tuple(DealCurrencyItemDTO(*v) for v in self._catalog.list())
        )
