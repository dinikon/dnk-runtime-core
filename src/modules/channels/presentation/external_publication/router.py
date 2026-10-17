from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.channels.presentation.external_publication.http.controller.list_publications import (
    list_publications,
)
from src.modules.channels.presentation.external_publication.http.controller.get_publication import (
    get_publication,
)
from src.modules.channels.presentation.external_publication.http.response.list_publications import (
    ListPublicationsResponse,
)
from src.modules.channels.presentation.external_publication.http.response.get_publication import (
    GetPublicationResponse,
)

router = APIRouter(
    prefix="/channels/{channel_id}/publications",
    tags=["channels"],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "", list_publications, methods=["GET"], response_model=ListPublicationsResponse
)
router.add_api_route(
    "/{publication_id}",
    get_publication,
    methods=["GET"],
    response_model=GetPublicationResponse,
)
