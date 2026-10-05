from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.reference_data.presentation.locale.http.controller.list_locales import (
    list_locales,
)
from src.modules.reference_data.presentation.locale.http.response.locale import (
    LocaleResponse,
)

router = APIRouter(tags=["reference-data"])
router.add_api_route(
    "/locales",
    list_locales,
    methods=["GET"],
    response_model=list[LocaleResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
