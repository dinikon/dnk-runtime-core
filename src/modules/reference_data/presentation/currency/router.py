from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.reference_data.presentation.currency.http.controller.list_currencies import (
    list_currencies,
)
from src.modules.reference_data.presentation.currency.http.response.currency import (
    CurrencyResponse,
)

router = APIRouter(tags=["reference-data"])
router.add_api_route(
    "/currencies",
    list_currencies,
    methods=["GET"],
    response_model=list[CurrencyResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
