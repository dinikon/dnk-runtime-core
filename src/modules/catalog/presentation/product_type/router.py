from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.catalog.presentation.product_type.http.controller.create_product_type import (
    create_product_type,
)
from src.modules.catalog.presentation.product_type.http.response.create_product_type import (
    CreateProductTypeResponse,
)
from src.modules.catalog.presentation.product_type.http.controller.delete_product_type import (
    delete_product_type,
)
from src.modules.catalog.presentation.product_type.http.controller.put_product_type_translation import (
    put_product_type_translation,
)
from src.modules.catalog.presentation.product_type.http.response.put_product_type_translation import (
    PutProductTypeTranslationResponse,
)
from src.modules.catalog.presentation.product_type.http.controller.replace_product_type_schema import (
    replace_product_type_schema,
)
from src.modules.catalog.presentation.product_type.http.response.replace_product_type_schema import (
    ReplaceProductTypeSchemaResponse,
)
from src.modules.catalog.presentation.product_type.http.controller.get_product_type import (
    get_product_type,
)
from src.modules.catalog.presentation.product_type.http.response.get_product_type import (
    GetProductTypeResponse,
)
from src.modules.catalog.presentation.product_type.http.controller.list_product_types import (
    list_product_types,
)
from src.modules.catalog.presentation.product_type.http.response.list_product_types import (
    ListProductTypesResponse,
)

router = APIRouter(prefix="/catalog/product-types", tags=["catalog-product_type"])
router.add_api_route(
    "",
    create_product_type,
    methods=["POST"],
    status_code=201,
    response_model=CreateProductTypeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_type_id}",
    delete_product_type,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_type_id}/translations/{locale}",
    put_product_type_translation,
    methods=["PUT"],
    status_code=200,
    response_model=PutProductTypeTranslationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_type_id}/schema",
    replace_product_type_schema,
    methods=["PUT"],
    status_code=200,
    response_model=ReplaceProductTypeSchemaResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{product_type_id}",
    get_product_type,
    methods=["GET"],
    status_code=200,
    response_model=GetProductTypeResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    list_product_types,
    methods=["GET"],
    status_code=200,
    response_model=ListProductTypesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
