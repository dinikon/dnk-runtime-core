from fastapi import APIRouter, Depends

from src.modules.catalog.presentation.product_type.http.controller.create_type import (
    create_type,
)
from src.modules.catalog.presentation.product_type.http.controller.delete_type import (
    delete_type,
)
from src.modules.catalog.presentation.product_type.http.controller.get_type import (
    get_type,
)
from src.modules.catalog.presentation.product_type.http.controller.list_types import (
    list_types,
)
from src.modules.catalog.presentation.product_type.http.controller.put_type import (
    put_type,
)
from src.modules.catalog.presentation.product_type.http.response.contract import (
    ProductTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/catalog/product-types", tags=["catalog-product-types"])

router.add_api_route(
    "",
    list_types,
    methods=["GET"],
    response_model=list[ProductTypeResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_type,
    methods=["POST"],
    status_code=201,
    response_model=ProductTypeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{type_id}",
    get_type,
    methods=["GET"],
    response_model=ProductTypeResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{type_id}",
    put_type,
    methods=["PUT"],
    response_model=ProductTypeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{type_id}",
    delete_type,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
