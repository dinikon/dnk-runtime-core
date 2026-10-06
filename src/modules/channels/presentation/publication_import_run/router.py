from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.publication_import_run.http.controller.start_publication_import import (
    start_publication_import,
)
from src.modules.channels.presentation.publication_import_run.http.controller.get_publication_import_run import (
    get_publication_import_run,
)
from src.modules.channels.presentation.publication_import_run.http.controller.get_latest_publication_import import (
    get_latest_publication_import,
)
from src.modules.channels.presentation.publication_import_run.http.response.start_publication_import import (
    StartPublicationImportResponse,
)
from src.modules.channels.presentation.publication_import_run.http.response.get_publication_import_run import (
    GetPublicationImportRunResponse,
)
from src.modules.channels.presentation.publication_import_run.http.response.get_latest_publication_import import (
    GetLatestPublicationImportResponse,
)

router = APIRouter(
    prefix="/channels/{channel_id}/publication-imports",
    tags=["channels"],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    start_publication_import,
    methods=["POST"],
    response_model=StartPublicationImportResponse,
    status_code=202,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/latest",
    get_latest_publication_import,
    methods=["GET"],
    response_model=GetLatestPublicationImportResponse | None,
)
router.add_api_route(
    "/{run_id}",
    get_publication_import_run,
    methods=["GET"],
    response_model=GetPublicationImportRunResponse,
)
