from fastapi import APIRouter, Depends
from src.modules.channels.presentation.http_route import ChannelsRoute
from src.modules.channels.presentation.depends.access import (
    require_channels_read_context,
)
from src.modules.channels.presentation.external_publication.http.controller.get_external_publication import (
    get_external_publication,
)
from src.modules.channels.presentation.external_publication.http.response.get_external_publication import (
    GetExternalPublicationResponse,
)
from src.modules.channels.presentation.external_publication.http.controller.list_external_publications import (
    list_external_publications,
)
from src.modules.channels.presentation.external_publication.http.response.list_external_publications import (
    ListExternalPublicationsResponse,
)

router = APIRouter(prefix="/channels", tags=["channels"], route_class=ChannelsRoute)
router.add_api_route(
    "/publications/{publication_id}",
    get_external_publication,
    methods=["GET"],
    status_code=200,
    response_model=GetExternalPublicationResponse,
    dependencies=[Depends(require_channels_read_context)],
)
router.add_api_route(
    "/connections/{connection_id}/publications",
    list_external_publications,
    methods=["GET"],
    status_code=200,
    response_model=ListExternalPublicationsResponse,
    dependencies=[Depends(require_channels_read_context)],
)
