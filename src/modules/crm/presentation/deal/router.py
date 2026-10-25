from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.crm.presentation.deal.http.controller.list_deals import list_deals
from src.modules.crm.presentation.deal.http.response.list_deal import ListDealsResponse
from src.modules.crm.presentation.deal.http.controller.create_deal import create_deal
from src.modules.crm.presentation.deal.http.response.create_deal import (
    CreateDealResponse,
)
from src.modules.crm.presentation.deal.http.controller.get_deal import get_deal
from src.modules.crm.presentation.deal.http.response.get_deal import GetDealResponse
from src.modules.crm.presentation.deal.http.controller.patch_deal import patch_deal
from src.modules.crm.presentation.deal.http.response.patch_deal import PatchDealResponse
from src.modules.crm.presentation.deal.http.controller.move_deal import move_deal
from src.modules.crm.presentation.deal.http.response.move_deal import MoveDealResponse
from src.modules.crm.presentation.deal.http.controller.change_funnel_deal import (
    change_funnel_deal,
)
from src.modules.crm.presentation.deal.http.response.change_funnel_deal import (
    ChangeFunnelDealResponse,
)

router = APIRouter(prefix="/crm/deals", tags=["crm-deals"])
router.add_api_route(
    "",
    list_deals,
    methods=["GET"],
    response_model=ListDealsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_deal,
    methods=["POST"],
    response_model=CreateDealResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
    status_code=201,
)
router.add_api_route(
    "/{deal_id}",
    get_deal,
    methods=["GET"],
    response_model=GetDealResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{deal_id}",
    patch_deal,
    methods=["PATCH"],
    response_model=PatchDealResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{deal_id}/stage",
    move_deal,
    methods=["PUT"],
    response_model=MoveDealResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{deal_id}/funnel",
    change_funnel_deal,
    methods=["PUT"],
    response_model=ChangeFunnelDealResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
