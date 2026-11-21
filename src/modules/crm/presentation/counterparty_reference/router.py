from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.crm.presentation.counterparty_reference.http.controller.search_counterparty_references import (
    search_counterparty_references,
)
from src.modules.crm.presentation.counterparty_reference.http.response.search_counterparty_references import (
    SearchCounterpartyReferencesResponse,
)

router = APIRouter(
    prefix="/crm/counterparty-references", tags=["crm-counterparty-references"]
)
router.add_api_route(
    "",
    search_counterparty_references,
    methods=["GET"],
    response_model=SearchCounterpartyReferencesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
