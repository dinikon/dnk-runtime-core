from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.reference_data.presentation.time_zone.http.controller.list_time_zones import (
    list_time_zones,
)
from src.modules.reference_data.presentation.time_zone.http.response.time_zone import (
    TimeZoneResponse,
)

router = APIRouter(tags=["reference-data"])
router.add_api_route(
    "/time-zones",
    list_time_zones,
    methods=["GET"],
    response_model=list[TimeZoneResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
