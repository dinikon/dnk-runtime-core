from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.crm.presentation.deal.http.controller.list_deal_currencies import (
    list_deal_currencies,
)
from src.modules.crm.presentation.deal.http.response.list_deal_currencies import (
    ListDealCurrenciesResponse,
)

router = APIRouter()
router.add_api_route(
    "/crm/deal-currencies",
    list_deal_currencies,
    methods=["GET"],
    response_model=ListDealCurrenciesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
