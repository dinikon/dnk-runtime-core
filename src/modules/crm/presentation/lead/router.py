from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.crm.presentation.lead.http.controller.list_leads import list_leads
from src.modules.crm.presentation.lead.http.response.list_lead import ListLeadsResponse
from src.modules.crm.presentation.lead.http.controller.create_lead import create_lead
from src.modules.crm.presentation.lead.http.response.create_lead import (
    CreateLeadResponse,
)
from src.modules.crm.presentation.lead.http.controller.get_lead import get_lead
from src.modules.crm.presentation.lead.http.response.get_lead import GetLeadResponse
from src.modules.crm.presentation.lead.http.controller.patch_lead import patch_lead
from src.modules.crm.presentation.lead.http.response.patch_lead import PatchLeadResponse
from src.modules.crm.presentation.lead.http.controller.move_lead import move_lead
from src.modules.crm.presentation.lead.http.response.move_lead import MoveLeadResponse
from src.modules.crm.presentation.lead.http.controller.change_funnel_lead import (
    change_funnel_lead,
)
from src.modules.crm.presentation.lead.http.response.change_funnel_lead import (
    ChangeFunnelLeadResponse,
)
from src.modules.crm.presentation.lead.http.controller.get_conversion_context import (
    get_conversion_context,
)
from src.modules.crm.presentation.lead.http.controller.convert_lead import convert_lead
from src.modules.crm.presentation.lead.http.response.get_conversion_context import (
    GetLeadConversionContextResponse,
)
from src.modules.crm.presentation.lead.http.response.convert_lead import (
    ConvertLeadResponse,
)

router = APIRouter(prefix="/crm/leads", tags=["crm-leads"])
router.add_api_route(
    "",
    list_leads,
    methods=["GET"],
    response_model=ListLeadsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_lead,
    methods=["POST"],
    response_model=CreateLeadResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
    status_code=201,
)
router.add_api_route(
    "/{lead_id}",
    get_lead,
    methods=["GET"],
    response_model=GetLeadResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{lead_id}",
    patch_lead,
    methods=["PATCH"],
    response_model=PatchLeadResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{lead_id}/stage",
    move_lead,
    methods=["PUT"],
    response_model=MoveLeadResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{lead_id}/funnel",
    change_funnel_lead,
    methods=["PUT"],
    response_model=ChangeFunnelLeadResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{lead_id}/conversion-context",
    get_conversion_context,
    methods=["GET"],
    response_model=GetLeadConversionContextResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{lead_id}/convert",
    convert_lead,
    methods=["POST"],
    response_model=ConvertLeadResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
