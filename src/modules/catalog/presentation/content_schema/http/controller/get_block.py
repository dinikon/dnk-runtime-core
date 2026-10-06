from uuid import UUID


from src.modules.catalog.presentation.content_schema.depends import (
    ContentSchemaServiceDep,
)
from src.modules.catalog.presentation.content_schema.http.context import (
    require_tenant,
    raise_schema_http_error,
)
from src.modules.catalog.presentation.content_schema.http.response.block import (
    BlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_block(
    block_id: UUID,
    context: AuthenticatedRequestContextDep,
    service: ContentSchemaServiceDep,
) -> BlockResponse:
    require_tenant(context)
    try:
        item = await service.get_block(block_id)
    except Exception as exc:
        raise_schema_http_error(exc)
    return BlockResponse.from_dto(item)
