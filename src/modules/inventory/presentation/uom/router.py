from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.inventory.presentation.uom.http.controller.list_uoms import list_uoms
from src.modules.inventory.presentation.uom.http.response.list_uoms import (
    ListUomsResponse,
)

router = APIRouter(prefix="/inventory/uoms", tags=["inventory-uoms"])
router.add_api_route(
    "",
    list_uoms,
    methods=["GET"],
    response_model=ListUomsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
