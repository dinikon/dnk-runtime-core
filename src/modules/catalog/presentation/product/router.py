from fastapi import APIRouter, Depends

from src.modules.catalog.presentation.product.http.controller.create_product import (
    create_product,
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
    "/{product_id}/contents/{locale}",
    put_product_content,
    methods=["PUT"],
    response_model=PutProductContentResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
