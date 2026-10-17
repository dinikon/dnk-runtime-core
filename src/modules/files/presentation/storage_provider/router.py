from fastapi import APIRouter, Depends
from src.modules.files.presentation.depends.admin import require_files_admin_context
from src.modules.files.presentation.storage_provider.http.controller.list_providers import (
    list_providers,
)
from src.modules.files.presentation.storage_provider.http.response.list_providers import (
    ListProvidersItemResponse,
)

router = APIRouter(tags=["Files"])
router.add_api_route(
    "/files/providers/",
    list_providers,
    methods=["GET"],
    response_model=list[ListProvidersItemResponse],
    dependencies=[Depends(require_files_admin_context)],
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}},
)
