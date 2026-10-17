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
from src.modules.catalog.presentation.catalog_item.http.controller.create_simple_catalog_item import (
    create_simple_catalog_item,
)
from src.modules.catalog.presentation.catalog_item.http.response.create_simple_catalog_item import (
    CreateSimpleCatalogItemResponse,
)

router.add_api_route(
    "/simple",
    create_simple_catalog_item,
    methods=["POST"],
    status_code=201,
    response_model=CreateSimpleCatalogItemResponse,
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
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_sku import (
    set_catalog_item_sku,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_sku import (
    SetCatalogItemSkuResponse,
)

router.add_api_route(
    "/{item_id}/sku",
    set_catalog_item_sku,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemSkuResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_tags import (
    set_catalog_item_tags,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_tags import (
    SetCatalogItemTagsResponse,
)

router.add_api_route(
    "/{item_id}/tags",
    set_catalog_item_tags,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemTagsResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_price import (
    set_catalog_item_price,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_price import (
    SetCatalogItemPriceResponse,
)

router.add_api_route(
    "/{item_id}/price",
    set_catalog_item_price,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemPriceResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_stock import (
    set_catalog_item_stock,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_stock import (
    SetCatalogItemStockResponse,
)

router.add_api_route(
    "/{item_id}/stock",
    set_catalog_item_stock,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemStockResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_status import (
    set_catalog_item_status,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_status import (
    SetCatalogItemStatusResponse,
)

router.add_api_route(
    "/{item_id}/status",
    set_catalog_item_status,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemStatusResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_virtual import (
    set_catalog_item_virtual,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_virtual import (
    SetCatalogItemVirtualResponse,
)

router.add_api_route(
    "/{item_id}/virtual",
    set_catalog_item_virtual,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemVirtualResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_metadata import (
    set_catalog_item_metadata,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_metadata import (
    SetCatalogItemMetadataResponse,
)

router.add_api_route(
    "/{item_id}/metadata",
    set_catalog_item_metadata,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemMetadataResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_attributes import (
    set_catalog_item_attributes,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_attributes import (
    SetCatalogItemAttributesResponse,
)

router.add_api_route(
    "/{item_id}/attributes",
    set_catalog_item_attributes,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemAttributesResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_categories import (
    set_catalog_item_categories,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_categories import (
    SetCatalogItemCategoriesResponse,
)

router.add_api_route(
    "/{item_id}/categories",
    set_catalog_item_categories,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemCategoriesResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_measurements import (
    set_catalog_item_measurements,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_measurements import (
    SetCatalogItemMeasurementsResponse,
)

router.add_api_route(
    "/{item_id}/measurements",
    set_catalog_item_measurements,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemMeasurementsResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.delete_catalog_item_content import (
    delete_catalog_item_content,
)

router.add_api_route(
    "/{item_id}/content/{locale}",
    delete_catalog_item_content,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.put_catalog_item_content import (
    put_catalog_item_content,
)
from src.modules.catalog.presentation.catalog_item.http.response.put_catalog_item_content import (
    PutCatalogItemContentResponse,
)

router.add_api_route(
    "/{item_id}/content/{locale}",
    put_catalog_item_content,
    methods=["PUT"],
    status_code=200,
    response_model=PutCatalogItemContentResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.delete_catalog_item_gallery import (
    delete_catalog_item_gallery,
)

router.add_api_route(
    "/{item_id}/gallery/{locale}",
    delete_catalog_item_gallery,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
from src.modules.catalog.presentation.catalog_item.http.controller.replace_catalog_item_gallery import (
    replace_catalog_item_gallery,
)
from src.modules.catalog.presentation.catalog_item.http.response.replace_catalog_item_gallery import (
    ReplaceCatalogItemGalleryResponse,
)

router.add_api_route(
    "/{item_id}/gallery/{locale}",
    replace_catalog_item_gallery,
    methods=["PUT"],
    status_code=200,
    response_model=ReplaceCatalogItemGalleryResponse,
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
from src.modules.catalog.presentation.catalog_item.http.controller.set_catalog_item_primary_image import (
    set_catalog_item_primary_image,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_primary_image import (
    SetCatalogItemPrimaryImageResponse,
)

router.add_api_route(
    "/{item_id}/gallery/{locale}/primary",
    set_catalog_item_primary_image,
    methods=["PUT"],
    status_code=200,
    response_model=SetCatalogItemPrimaryImageResponse,
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
