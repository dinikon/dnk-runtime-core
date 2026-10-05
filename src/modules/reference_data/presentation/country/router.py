from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.reference_data.presentation.country.http.controller.list_countries import (
    list_countries,
)
from src.modules.reference_data.presentation.country.http.response.country import (
    CountryResponse,
)

router = APIRouter(tags=["reference-data"])
router.add_api_route(
    "/countries",
    list_countries,
    methods=["GET"],
    response_model=list[CountryResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
