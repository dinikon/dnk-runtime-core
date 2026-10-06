from fastapi import APIRouter, Depends

from src.modules.catalog.presentation.content_block.http.controller.create_block import (
    create_block,
)
from src.modules.catalog.presentation.content_block.http.controller.delete_block import (
    delete_block,
)
from src.modules.catalog.presentation.content_block.http.controller.get_block import (
    get_block,
)
from src.modules.catalog.presentation.content_block.http.controller.list_blocks import (
    list_blocks,
)
from src.modules.catalog.presentation.content_block.http.controller.put_block import (
    put_block,
)
from src.modules.catalog.presentation.content_block.http.response.contract import (
    BlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/catalog/content-blocks", tags=["catalog-content-blocks"])

router.add_api_route(
    "",
    list_blocks,
    methods=["GET"],
    response_model=list[BlockResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
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
router.add_api_route(
    "/{block_id}",
    get_block,
    methods=["GET"],
    response_model=BlockResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{block_id}",
    put_block,
    methods=["PUT"],
    response_model=BlockResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{block_id}",
    delete_block,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
