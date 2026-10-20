from fastapi import APIRouter, Depends
from src.modules.channels.presentation.http_route import ChannelsRoute
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.product_representation.http.controller.list_catalog_candidates import (
    list_catalog_candidates,
)
from src.modules.channels.presentation.product_representation.http.response.list_catalog_candidates import (
    ListCatalogCandidatesResponse,
)
from src.modules.channels.presentation.product_representation.http.controller.preview_catalog_draft import (
    preview_catalog_draft,
)
from src.modules.channels.presentation.product_representation.http.response.preview_catalog_draft import (
    PreviewCatalogDraftResponse,
)
from src.modules.channels.presentation.product_representation.http.controller.bind_existing_publication import (
    bind_existing_publication,
)
from src.modules.channels.presentation.product_representation.http.response.bind_existing_publication import (
    BindExistingPublicationResponse,
)
from src.modules.channels.presentation.product_representation.http.controller.unbind_publication import (
    unbind_publication,
)
from src.modules.channels.presentation.product_representation.http.controller.create_catalog_item_from_publication import (
    create_catalog_item_from_publication,
)
from src.modules.channels.presentation.product_representation.http.response.create_catalog_item_from_publication import (
    CreateCatalogItemFromPublicationResponse,
)

router = APIRouter(
    prefix="/channels/publications", tags=["channels"], route_class=ChannelsRoute
)
router.add_api_route(
    "/{publication_id}/catalog-candidates",
    list_catalog_candidates,
    methods=["GET"],
    status_code=200,
    response_model=ListCatalogCandidatesResponse,
)
router.add_api_route(
    "/{publication_id}/catalog-draft-preview",
    preview_catalog_draft,
    methods=["GET"],
    status_code=200,
    response_model=PreviewCatalogDraftResponse,
)
router.add_api_route(
    "/{publication_id}/binding",
    bind_existing_publication,
    methods=["POST"],
    status_code=201,
    response_model=BindExistingPublicationResponse,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{publication_id}/binding",
    unbind_publication,
    methods=["DELETE"],
    status_code=204,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{publication_id}/catalog-item",
    create_catalog_item_from_publication,
    methods=["POST"],
    status_code=201,
    response_model=CreateCatalogItemFromPublicationResponse,
    dependencies=[Depends(require_csrf)],
)
