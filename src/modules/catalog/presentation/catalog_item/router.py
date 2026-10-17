from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/catalog/items", tags=["catalog-item"])

from src.modules.catalog.presentation.catalog_item.http.controller.list_catalog_items import (
    list_catalog_items,
)
from src.modules.catalog.presentation.catalog_item.http.response.list_catalog_items import (
    ListCatalogItemsResponse,
)

router.add_api_route(
    "",
    list_catalog_items,
    methods=["GET"],
    status_code=200,
    response_model=ListCatalogItemsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

from src.modules.catalog.presentation.catalog_item.http.controller.create_catalog_item import (
    create_catalog_item,
)
from src.modules.catalog.presentation.catalog_item.http.response.create_catalog_item import (
    CreateCatalogItemResponse,
)

router.add_api_route(
    "",
    create_catalog_item,
    methods=["POST"],
    status_code=201,
    response_model=CreateCatalogItemResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_item.http.controller.get_catalog_item import (
    get_catalog_item,
)
from src.modules.catalog.presentation.catalog_item.http.response.get_catalog_item import (
    GetCatalogItemResponse,
)

router.add_api_route(
    "/{item_id}",
    get_catalog_item,
    methods=["GET"],
    status_code=200,
    response_model=GetCatalogItemResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

from src.modules.catalog.presentation.catalog_item.http.controller.update_catalog_item import (
    update_catalog_item,
)
from src.modules.catalog.presentation.catalog_item.http.response.update_catalog_item import (
    UpdateCatalogItemResponse,
)

router.add_api_route(
    "/{item_id}",
    update_catalog_item,
    methods=["PATCH"],
    status_code=200,
    response_model=UpdateCatalogItemResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_item.http.controller.delete_catalog_item import (
    delete_catalog_item,
)

router.add_api_route(
    "/{item_id}",
    delete_catalog_item,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_item.http.controller.upload_catalog_item_image import (
    upload_catalog_item_image,
)
from src.modules.catalog.presentation.catalog_item.http.response.upload_catalog_item_image import (
    UploadCatalogItemImageResponse,
)

router.add_api_route(
    "/{item_id}/images/{locale}/upload",
    upload_catalog_item_image,
    methods=["POST"],
    status_code=201,
    response_model=UploadCatalogItemImageResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_item.http.controller.get_catalog_item_image_content import (
    get_catalog_item_image_content,
)

router.add_api_route(
    "/{item_id}/images/{locale}/{image_id}/content",
    get_catalog_item_image_content,
    methods=["GET"],
    status_code=200,
    dependencies=[Depends(require_authenticated_request_context)],
)
