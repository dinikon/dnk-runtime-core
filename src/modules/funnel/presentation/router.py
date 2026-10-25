from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.funnel.presentation.http.controller.create_funnel import create_funnel
from src.modules.funnel.presentation.http.response.create_funnel import (
    CreateFunnelResponse,
)
from src.modules.funnel.presentation.http.controller.update_funnel import update_funnel
from src.modules.funnel.presentation.http.response.update_funnel import (
    UpdateFunnelResponse,
)
from src.modules.funnel.presentation.http.controller.get_funnel import get_funnel
from src.modules.funnel.presentation.http.response.get_funnel import GetFunnelResponse
from src.modules.funnel.presentation.http.controller.list_funnels import list_funnels
from src.modules.funnel.presentation.http.response.list_funnels import (
    ListFunnelsResponse,
)

router = APIRouter(prefix="/funnels", tags=["funnels"])
router.add_api_route(
    "",
    create_funnel,
    methods=["POST"],
    response_model=CreateFunnelResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
    status_code=201,
)
router.add_api_route(
    "/{funnel_id}",
    update_funnel,
    methods=["PUT"],
    response_model=UpdateFunnelResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{funnel_id}",
    get_funnel,
    methods=["GET"],
    response_model=GetFunnelResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    list_funnels,
    methods=["GET"],
    response_model=ListFunnelsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
