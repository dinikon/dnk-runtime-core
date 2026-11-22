from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.feed_builder.presentation.feed.http.schema.body_limit import (
    SchemaBodyLimitRoute,
)
from src.modules.feed_builder.presentation.feed.export_depends import (
    prepare_export_transaction,
)
from src.modules.feed_builder.presentation.publication.http.controller.get_publication_fields import (
    get_publication_fields,
)
from src.modules.feed_builder.presentation.publication.http.controller.set_publication_override import (
    set_publication_override,
)
from src.modules.feed_builder.presentation.publication.http.controller.reset_publication_override import (
    reset_publication_override,
)
from src.modules.feed_builder.presentation.publication.http.response.get_publication_fields import (
    GetPublicationFieldsResponse,
)
from src.modules.feed_builder.presentation.publication.http.response.set_publication_override import (
    SetPublicationOverrideResponse,
)
from src.modules.feed_builder.presentation.publication.http.response.reset_publication_override import (
    ResetPublicationOverrideResponse,
)
from src.modules.feed_builder.presentation.publication.http.controller.add_catalog_items import (
    add_catalog_items,
)
from src.modules.feed_builder.presentation.publication.http.response.add_catalog_items import (
    AddCatalogItemsResponse,
)
from src.modules.feed_builder.presentation.publication.http.controller.list_publications import (
    list_publications,
)
from src.modules.feed_builder.presentation.publication.http.response.list_publications import (
    ListPublicationsResponse,
)
from src.modules.feed_builder.presentation.publication.http.controller.get_publication import (
    get_publication,
)
from src.modules.feed_builder.presentation.publication.http.response.get_publication import (
    GetPublicationResponse,
)
from src.modules.feed_builder.presentation.publication.http.controller.change_publication_status import (
    change_publication_status,
)
from src.modules.feed_builder.presentation.publication.http.response.change_publication_status import (
    ChangePublicationStatusResponse,
)
from src.modules.feed_builder.presentation.publication.http.controller.remove_publication import (
    remove_publication,
)
from src.modules.feed_builder.presentation.publication.http.controller.restore_publication import (
    restore_publication,
)
from src.modules.feed_builder.presentation.publication.http.response.restore_publication import (
    RestorePublicationResponse,
)
from src.modules.feed_builder.presentation.publication.http.controller.variant_selection import (
    variant_selection,
)
from src.modules.feed_builder.presentation.publication.http.response.variant_selection import (
    VariantSelectionResponse,
)

router = APIRouter(
    prefix="/feed-builder", tags=["feed-publications"], route_class=SchemaBodyLimitRoute
)
router.add_api_route(
    "/feeds/{feed_id}/publications",
    add_catalog_items,
    methods=["POST"],
    response_model=AddCatalogItemsResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/feeds/{feed_id}/publications",
    list_publications,
    methods=["GET"],
    response_model=ListPublicationsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/publications/{publication_id}",
    get_publication,
    methods=["GET"],
    response_model=GetPublicationResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/publications/{publication_id}/status",
    change_publication_status,
    methods=["PATCH"],
    response_model=ChangePublicationStatusResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/publications/{publication_id}/fields",
    get_publication_fields,
    methods=["GET"],
    response_model=GetPublicationFieldsResponse,
    dependencies=[
        Depends(prepare_export_transaction),
        Depends(require_authenticated_request_context),
    ],
)
router.add_api_route(
    "/publications/{publication_id}/overrides/{field_id}",
    set_publication_override,
    methods=["PUT"],
    response_model=SetPublicationOverrideResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/publications/{publication_id}/overrides/{field_id}",
    reset_publication_override,
    methods=["DELETE"],
    response_model=ResetPublicationOverrideResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/publications/{publication_id}",
    remove_publication,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/publications/{publication_id}/restore",
    restore_publication,
    methods=["POST"],
    response_model=RestorePublicationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/feeds/{feed_id}/variant-selection/{catalog_item_id}",
    variant_selection,
    methods=["GET"],
    response_model=VariantSelectionResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
