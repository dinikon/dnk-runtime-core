from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.content_block.query.get_content_block.query import (
    GetContentBlockQuery,
)
from src.modules.catalog.domain.content_block.error import (
    ContentBlockNotFoundError,
    ContentBlockConflictError,
    InvalidContentBlockError,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.presentation.content_block.depends import (
    GetContentBlockHandlerDep,
)
from src.modules.catalog.presentation.content_block.http.response.get_block import (
    GetBlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_block(
    block_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetContentBlockHandlerDep,
) -> GetBlockResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        item = await handler.execute(
            GetContentBlockQuery(ContentBlockIdVO.from_value(block_id))
        )
    except ContentBlockNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetBlockResponse.from_dto(item)
