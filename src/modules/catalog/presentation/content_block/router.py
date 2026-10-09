from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.catalog.presentation.content_block.http.controller.create_content_block import (
    create_content_block,
)
from src.modules.catalog.presentation.content_block.http.response.create_content_block import (
    CreateContentBlockResponse,
)
from src.modules.catalog.presentation.content_block.http.controller.delete_content_block import (
    delete_content_block,
)
from src.modules.catalog.presentation.content_block.http.controller.update_content_block import (
    update_content_block,
)
from src.modules.catalog.presentation.content_block.http.response.update_content_block import (
    UpdateContentBlockResponse,
)
from src.modules.catalog.presentation.content_block.http.controller.get_content_block import (
    get_content_block,
)
from src.modules.catalog.presentation.content_block.http.response.get_content_block import (
    GetContentBlockResponse,
)
from src.modules.catalog.presentation.content_block.http.controller.list_content_blocks import (
    list_content_blocks,
)
from src.modules.catalog.presentation.content_block.http.response.list_content_blocks import (
    ListContentBlocksResponse,
)

router = APIRouter(prefix="/catalog/content-blocks", tags=["catalog-content_block"])
router.add_api_route(
    "",
    create_content_block,
    methods=["POST"],
    status_code=201,
    response_model=CreateContentBlockResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{content_block_id}",
    delete_content_block,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{content_block_id}",
    update_content_block,
    methods=["PUT"],
    status_code=200,
    response_model=UpdateContentBlockResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{content_block_id}",
    get_content_block,
    methods=["GET"],
    status_code=200,
    response_model=GetContentBlockResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    list_content_blocks,
    methods=["GET"],
    status_code=200,
    response_model=ListContentBlocksResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
