"""HTTP-маршруты агрегата Channels."""

from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.channels.presentation.http.safe_route import ChannelsRoute
from src.modules.channels.presentation.external_publication.http.controller.list_publications import (
    list_publications,
)
from src.modules.channels.presentation.external_publication.http.response.list_publications import (
    ListPublicationsResponse,
)
from src.modules.channels.presentation.external_publication.http.controller.get_publication import (
    get_publication,
)
from src.modules.channels.presentation.external_publication.http.response.get_publication import (
    GetPublicationResponse,
)

router = APIRouter(
    prefix="/channels/{channel_id}", tags=["channels"], route_class=ChannelsRoute
)
router.add_api_route(
    "/publications",
    list_publications,
    methods=["GET"],
    status_code=200,
    response_model=ListPublicationsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/publications/{publication_id}",
    get_publication,
    methods=["GET"],
    status_code=200,
    response_model=GetPublicationResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
