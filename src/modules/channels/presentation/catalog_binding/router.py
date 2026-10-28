from src.modules.channels.presentation.catalog_binding.http.controller.list_channel_catalog_bindings import (
    list_channel_catalog_bindings,
)
from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.catalog_binding.http.route import BindingRoute
from src.modules.channels.presentation.catalog_binding.http.controller.create_catalog_binding import (
    create_catalog_binding,
)
from src.modules.channels.presentation.catalog_binding.http.response.create_catalog_binding import (
    CreateCatalogBindingResponse,
)
from src.modules.channels.presentation.catalog_binding.http.controller.update_catalog_binding import (
    update_catalog_binding,
)
from src.modules.channels.presentation.catalog_binding.http.response.update_catalog_binding import (
    UpdateCatalogBindingResponse,
)
from src.modules.channels.presentation.catalog_binding.http.controller.delete_catalog_binding import (
    delete_catalog_binding,
)
from src.modules.channels.presentation.catalog_binding.http.controller.get_catalog_binding import (
    get_catalog_binding,
)
from src.modules.channels.presentation.catalog_binding.http.response.get_catalog_binding import (
    GetCatalogBindingResponse,
)
from src.modules.channels.presentation.catalog_binding.http.controller.list_catalog_bindings import (
    list_catalog_bindings,
)
from src.modules.channels.presentation.catalog_binding.http.response.list_catalog_bindings import (
    ListCatalogBindingsResponse,
)
from src.modules.channels.presentation.catalog_binding.http.controller.preview_catalog_binding import (
    preview_catalog_binding,
)
from src.modules.channels.presentation.catalog_binding.http.response.preview_catalog_binding import (
    PreviewCatalogBindingResponse,
)
from src.modules.channels.presentation.catalog_binding.http.controller.list_catalog_binding_candidates import (
    list_catalog_binding_candidates,
)
from src.modules.channels.presentation.catalog_binding.http.response.list_catalog_binding_candidates import (
    ListCatalogBindingCandidatesResponse,
)
from src.modules.channels.presentation.catalog_binding.http.controller.list_publication_binding_candidates import (
    list_publication_binding_candidates,
)
from src.modules.channels.presentation.catalog_binding.http.response.list_publication_binding_candidates import (
    ListPublicationBindingCandidatesResponse,
)

router = APIRouter(
    prefix="/channels", tags=["catalog-bindings"], route_class=BindingRoute
)


router.add_api_route(
    "/{channel_id}/catalog-bindings",
    create_catalog_binding,
    methods=["POST"],
    status_code=201,
    response_model=CreateCatalogBindingResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}",
    update_catalog_binding,
    methods=["PUT"],
    status_code=200,
    response_model=UpdateCatalogBindingResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}",
    delete_catalog_binding,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}",
    get_catalog_binding,
    methods=["GET"],
    status_code=200,
    response_model=GetCatalogBindingResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)


router.add_api_route(
    "/catalog-bindings",
    list_catalog_bindings,
    methods=["GET"],
    status_code=200,
    response_model=ListCatalogBindingsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)


router.add_api_route(
    "/{channel_id}/catalog-bindings/preview",
    preview_catalog_binding,
    methods=["POST"],
    status_code=200,
    response_model=PreviewCatalogBindingResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/catalog-binding-candidates",
    list_catalog_binding_candidates,
    methods=["GET"],
    status_code=200,
    response_model=ListCatalogBindingCandidatesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)


router.add_api_route(
    "/{channel_id}/publication-binding-candidates",
    list_publication_binding_candidates,
    methods=["GET"],
    status_code=200,
    response_model=ListPublicationBindingCandidatesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

router.add_api_route(
    "/{channel_id}/catalog-bindings",
    list_channel_catalog_bindings,
    methods=["GET"],
    response_model=ListCatalogBindingsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
