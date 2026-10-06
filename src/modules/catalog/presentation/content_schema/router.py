from fastapi import APIRouter, Depends

from src.modules.catalog.presentation.content_schema.http.controller.create_block import (
    create_block,
)
from src.modules.catalog.presentation.content_schema.http.controller.create_type import (
    create_type,
)
from src.modules.catalog.presentation.content_schema.http.controller.delete_block import (
    delete_block,
)
from src.modules.catalog.presentation.content_schema.http.controller.delete_type import (
    delete_type,
)
from src.modules.catalog.presentation.content_schema.http.controller.get_block import (
    get_block,
)
from src.modules.catalog.presentation.content_schema.http.controller.get_type import (
    get_type,
)
from src.modules.catalog.presentation.content_schema.http.controller.list_blocks import (
    list_blocks,
)
from src.modules.catalog.presentation.content_schema.http.controller.list_types import (
    list_types,
)
from src.modules.catalog.presentation.content_schema.http.controller.put_block import (
    put_block,
)
from src.modules.catalog.presentation.content_schema.http.controller.put_type import (
    put_type,
)
from src.modules.catalog.presentation.content_schema.http.response.block import (
    BlockResponse,
)
from src.modules.catalog.presentation.content_schema.http.response.product_type import (
    ProductTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

blocks_router = APIRouter(
    prefix="/catalog/content-blocks", tags=["catalog-content-blocks"]
)
types_router = APIRouter(
    prefix="/catalog/product-types", tags=["catalog-product-types"]
)

blocks_router.add_api_route(
    "",
    list_blocks,
    methods=["GET"],
    response_model=list[BlockResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
blocks_router.add_api_route(
    "",
    create_block,
    methods=["POST"],
    status_code=201,
    response_model=BlockResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
blocks_router.add_api_route(
    "/{block_id}",
    get_block,
    methods=["GET"],
    response_model=BlockResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
blocks_router.add_api_route(
    "/{block_id}",
    put_block,
    methods=["PUT"],
    response_model=BlockResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
blocks_router.add_api_route(
    "/{block_id}",
    delete_block,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

types_router.add_api_route(
    "",
    list_types,
    methods=["GET"],
    response_model=list[ProductTypeResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
types_router.add_api_route(
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
types_router.add_api_route(
    "/{type_id}",
    get_type,
    methods=["GET"],
    response_model=ProductTypeResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
types_router.add_api_route(
    "/{type_id}",
    put_type,
    methods=["PUT"],
    response_model=ProductTypeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
types_router.add_api_route(
    "/{type_id}",
    delete_type,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
