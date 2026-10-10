from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.catalog.presentation.product.http.controller.create_simple_product import (
    create_simple_product,
)
from src.modules.catalog.presentation.product.http.response.create_simple_product import (
    CreateSimpleProductResponse,
)
from src.modules.catalog.presentation.product.http.controller.change_product_type import (
    change_product_type,
)
from src.modules.catalog.presentation.product.http.response.change_product_type import (
    ChangeProductTypeResponse,
)
from src.modules.catalog.presentation.product.http.controller.set_variant_properties import (
    set_variant_properties,
)
from src.modules.catalog.presentation.product.http.response.set_variant_properties import (
    SetVariantPropertiesResponse,
)
from src.modules.catalog.presentation.product.http.controller.put_product_content import (
    put_product_content,
)
from src.modules.catalog.presentation.product.http.response.put_product_content import (
    PutProductContentResponse,
)
from src.modules.catalog.presentation.product.http.controller.delete_product_content import (
    delete_product_content,
)
from src.modules.catalog.presentation.product.http.controller.put_variant_content import (
    put_variant_content,
)
from src.modules.catalog.presentation.product.http.response.put_variant_content import (
    PutVariantContentResponse,
)
from src.modules.catalog.presentation.product.http.controller.delete_variant_content import (
    delete_variant_content,
)
from src.modules.catalog.presentation.product.http.controller.delete_product import (
    delete_product,
)
from src.modules.catalog.presentation.product.http.controller.get_product import (
    get_product,
)
from src.modules.catalog.presentation.product.http.response.get_product import (
    GetProductResponse,
)
from src.modules.catalog.presentation.product.http.controller.list_products import (
    list_products,
)
from src.modules.catalog.presentation.product.http.response.list_products import (
    ListProductsResponse,
)
from src.modules.catalog.presentation.product.http.controller.get_variant import (
    get_variant,
)
from src.modules.catalog.presentation.product.http.response.get_variant import (
    GetVariantResponse,
)

router = APIRouter(prefix="/catalog/products", tags=["catalog-product"])
router.add_api_route(
    "/simple",
    create_simple_product,
    methods=["POST"],
    status_code=201,
    response_model=CreateSimpleProductResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/type",
    change_product_type,
    methods=["PUT"],
    status_code=200,
    response_model=ChangeProductTypeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/variants/{variant_id}/properties",
    set_variant_properties,
    methods=["PUT"],
    status_code=200,
    response_model=SetVariantPropertiesResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/content/{locale}",
    put_product_content,
    methods=["PUT"],
    status_code=200,
    response_model=PutProductContentResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/content/{locale}",
    delete_product_content,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/variants/{variant_id}/content/{locale}",
    put_variant_content,
    methods=["PUT"],
    status_code=200,
    response_model=PutVariantContentResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/variants/{variant_id}/content/{locale}",
    delete_variant_content,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}",
    delete_product,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}",
    get_product,
    methods=["GET"],
    status_code=200,
    response_model=GetProductResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    list_products,
    methods=["GET"],
    status_code=200,
    response_model=ListProductsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{product_id}/variants/{variant_id}",
    get_variant,
    methods=["GET"],
    status_code=200,
    response_model=GetVariantResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

from src.modules.catalog.presentation.product.http.controller.create_variable_product import (
    create_variable_product,
)
from src.modules.catalog.presentation.product.http.response.create_variable_product import (
    CreateVariableProductResponse,
)

router.add_api_route(
    "/variable",
    create_variable_product,
    methods=["POST"],
    status_code=201,
    response_model=CreateVariableProductResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.product.http.controller.replace_variants import (
    replace_variants,
)
from src.modules.catalog.presentation.product.http.response.replace_variants import (
    ReplaceVariantsResponse,
)

router.add_api_route(
    "/{product_id}/structure",
    replace_variants,
    methods=["PUT"],
    status_code=200,
    response_model=ReplaceVariantsResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.product.http.controller.change_product_kind import (
    change_product_kind,
)
from src.modules.catalog.presentation.product.http.response.change_product_kind import (
    ChangeProductKindResponse,
)

router.add_api_route(
    "/{product_id}/kind",
    change_product_kind,
    methods=["PUT"],
    status_code=200,
    response_model=ChangeProductKindResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.product.http.controller.set_product_attributes import (
    set_product_attributes,
)
from src.modules.catalog.presentation.product.http.response.set_product_attributes import (
    SetProductAttributesResponse,
)

router.add_api_route(
    "/{product_id}/attributes",
    set_product_attributes,
    methods=["PUT"],
    response_model=SetProductAttributesResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.product.http.controller.set_product_categories import (
    set_product_categories,
)
from src.modules.catalog.presentation.product.http.response.set_product_categories import (
    SetProductCategoriesResponse,
)

router.add_api_route(
    "/{product_id}/categories",
    set_product_categories,
    methods=["PUT"],
    response_model=SetProductCategoriesResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.product.http.controller.set_product_tags import (
    set_product_tags,
)
from src.modules.catalog.presentation.product.http.response.set_product_tags import (
    SetProductTagsResponse,
)

router.add_api_route(
    "/{product_id}/tags",
    set_product_tags,
    methods=["PUT"],
    response_model=SetProductTagsResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
