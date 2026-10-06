from fastapi import APIRouter, Depends

from src.modules.catalog.presentation.product.http.controller.create_product import (
    create_product,
)
from src.modules.catalog.presentation.product.http.controller.create_variable_product import (
    create_variable_product,
)
from src.modules.catalog.presentation.product.http.controller.list_products import (
    list_products,
)
from src.modules.catalog.presentation.product.http.controller.delete_product import (
    delete_product,
)
from src.modules.catalog.presentation.product.http.controller.put_variant_structure import (
    put_variant_structure,
)
from src.modules.catalog.presentation.product.http.controller.create_variant import (
    create_variant,
)
from src.modules.catalog.presentation.product.http.controller.get_variant import (
    get_variant,
)
from src.modules.catalog.presentation.product.http.controller.put_variant import (
    put_variant,
)
from src.modules.catalog.presentation.product.http.controller.delete_variant import (
    delete_variant,
)
from src.modules.catalog.presentation.product.http.controller.put_variant_content import (
    put_variant_content,
)
from src.modules.catalog.presentation.product.http.response.create_variable_product import (
    CreateVariableProductResponse,
)
from src.modules.catalog.presentation.product.http.response.list_products import (
    ListProductItemResponse,
)
from src.modules.catalog.presentation.product.http.response.put_variant_structure import (
    PutVariantStructureResponse,
)
from src.modules.catalog.presentation.product.http.response.create_variant import (
    CreateVariantResponse,
)
from src.modules.catalog.presentation.product.http.response.get_variant import (
    GetVariantResponse,
)
from src.modules.catalog.presentation.product.http.response.put_variant import (
    PutVariantResponse,
)
from src.modules.catalog.presentation.product.http.response.put_variant_content import (
    PutVariantContentResponse,
)
from src.modules.catalog.presentation.product.http.controller.get_product import (
    get_product,
)
from src.modules.catalog.presentation.product.http.controller.put_product_content import (
    put_product_content,
)
from src.modules.catalog.presentation.product.http.controller.put_product_categories import (
    put_product_categories,
)
from src.modules.catalog.presentation.product.http.response.put_product_categories import (
    PutProductCategoriesResponse,
)
from src.modules.catalog.presentation.product.http.response.create_product import (
    CreateProductResponse,
)
from src.modules.catalog.presentation.product.http.response.get_product import (
    GetProductResponse,
)
from src.modules.catalog.presentation.product.http.response.put_product_content import (
    PutProductContentResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/catalog/products", tags=["catalog-products"])
router.add_api_route(
    "",
    list_products,
    methods=["GET"],
    response_model=list[ListProductItemResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_product,
    methods=["POST"],
    status_code=201,
    response_model=CreateProductResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
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
router.add_api_route(
    "/{product_id}/categories",
    put_product_categories,
    methods=["PUT"],
    response_model=PutProductCategoriesResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}",
    get_product,
    methods=["GET"],
    response_model=GetProductResponse,
    dependencies=[Depends(require_authenticated_request_context)],
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
    "/{product_id}/variant-structure",
    put_variant_structure,
    methods=["PUT"],
    response_model=PutVariantStructureResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/variants",
    create_variant,
    methods=["POST"],
    status_code=201,
    response_model=CreateVariantResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/variants/{variant_id}",
    get_variant,
    methods=["GET"],
    response_model=GetVariantResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{product_id}/variants/{variant_id}",
    put_variant,
    methods=["PUT"],
    response_model=PutVariantResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/variants/{variant_id}",
    delete_variant,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/variants/{variant_id}/contents/{locale}",
    put_variant_content,
    methods=["PUT"],
    response_model=PutVariantContentResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_id}/contents/{locale}",
    put_product_content,
    methods=["PUT"],
    response_model=PutProductContentResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
