from typing import Annotated
from fastapi import Depends
from src.modules.crm.application.deal.query.list_deal_currencies.handler import (
    ListDealCurrenciesHandler,
)
from src.modules.crm.infrastructure.adapter.deal_currencies import (
    StaticDealCurrencyCatalog,
)


def get_list_deal_currencies_handler() -> ListDealCurrenciesHandler:
    """Внешняя сборка статической валютной политики."""
    return ListDealCurrenciesHandler(StaticDealCurrencyCatalog())


ListDealCurrenciesHandlerDep = Annotated[
    ListDealCurrenciesHandler, Depends(get_list_deal_currencies_handler)
]
