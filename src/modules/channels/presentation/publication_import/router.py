from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.http_route import ChannelsRoute
from src.modules.channels.presentation.publication_import.http.controller.start_publication_import import (
    start_publication_import,
)
from src.modules.channels.presentation.publication_import.http.response.start_publication_import import (
    StartPublicationImportResponse,
)
from src.modules.channels.presentation.publication_import.http.controller.retry_publication_import import (
    retry_publication_import,
)
from src.modules.channels.presentation.publication_import.http.response.retry_publication_import import (
    RetryPublicationImportResponse,
)
from src.modules.channels.presentation.publication_import.http.controller.cancel_publication_import import (
    cancel_publication_import,
)
from src.modules.channels.presentation.publication_import.http.response.cancel_publication_import import (
    CancelPublicationImportResponse,
)
from src.modules.channels.presentation.publication_import.http.controller.get_publication_import import (
    get_publication_import,
)
from src.modules.channels.presentation.publication_import.http.response.get_publication_import import (
    GetPublicationImportResponse,
)
from src.modules.channels.presentation.publication_import.http.response.get_publication_import_image import (
    PublicationImportImageResponse,
)
from src.modules.channels.presentation.publication_import.http.controller.get_publication_import_image import (
    get_publication_import_image,
)

router = APIRouter(prefix="/channels", tags=["channels"], route_class=ChannelsRoute)
router.add_api_route(
    "/publications/{publication_id}/import-preparations",
    start_publication_import,
    methods=["POST"],
    status_code=202,
    response_model=StartPublicationImportResponse,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/import-preparations/{preparation_id}",
    get_publication_import,
    methods=["GET"],
    response_model=GetPublicationImportResponse,
)
router.add_api_route(
    "/import-preparations/{preparation_id}/retry",
    retry_publication_import,
    methods=["POST"],
    response_model=RetryPublicationImportResponse,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/import-preparations/{preparation_id}/cancel",
    cancel_publication_import,
    methods=["POST"],
    response_model=CancelPublicationImportResponse,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/import-preparations/{preparation_id}/image",
    get_publication_import_image,
    methods=["GET"],
    response_class=PublicationImportImageResponse,
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}}}},
)
