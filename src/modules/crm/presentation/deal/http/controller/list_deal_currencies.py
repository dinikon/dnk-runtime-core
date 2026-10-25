from dataclasses import asdict
from typing import Annotated
from fastapi import Depends
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.application.deal.query.list_deal_currencies.handler import (
    ListDealCurrenciesHandler,
)
from src.modules.crm.application.deal.query.list_deal_currencies.query import (
    ListDealCurrenciesQuery,
)
from src.modules.crm.presentation.depends.currencies import ListDealCurrenciesHandlerDep
from src.modules.crm.presentation.deal.http.response.list_deal_currencies import (
    ListDealCurrenciesResponse,
)


async def list_deal_currencies(
    context: AuthenticatedRequestContextDep, handler: ListDealCurrenciesHandlerDep
) -> ListDealCurrenciesResponse:
    """Возвращает доступные валюты продаж авторизованному пользователю tenant."""
    sales_identity(context)
    result = await handler.execute(ListDealCurrenciesQuery())
    return ListDealCurrenciesResponse.model_validate(asdict(result))
