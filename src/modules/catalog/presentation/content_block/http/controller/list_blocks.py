from fastapi import HTTPException

from src.modules.catalog.application.content_block.query.list_content_blocks.query import (
    ListContentBlocksQuery,
)
from src.modules.catalog.domain.content_block.error import (
    ContentBlockNotFoundError,
    ContentBlockConflictError,
    InvalidContentBlockError,
)
from src.modules.catalog.presentation.content_block.depends import (
    ListContentBlocksHandlerDep,
)
from src.modules.catalog.presentation.content_block.http.response.list_block import (
    ListBlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_blocks(
    context: AuthenticatedRequestContextDep,
    handler: ListContentBlocksHandlerDep,
) -> list[ListBlockResponse]:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    items = await handler.execute(ListContentBlocksQuery())
    return [ListBlockResponse.from_dto(item) for item in items]
