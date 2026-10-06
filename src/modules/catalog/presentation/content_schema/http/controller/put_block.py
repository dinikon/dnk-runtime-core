from uuid import UUID


from src.modules.catalog.presentation.content_schema.depends import (
    ContentSchemaServiceDep,
)
from src.modules.catalog.presentation.content_schema.http.context import (
    require_tenant,
    raise_schema_http_error,
)
from src.modules.catalog.presentation.content_schema.http.request.put_block import (
    PutBlockRequest,
)
from src.modules.catalog.presentation.content_schema.http.response.block import (
    BlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def put_block(
    block_id: UUID,
    payload: PutBlockRequest,
    context: AuthenticatedRequestContextDep,
    service: ContentSchemaServiceDep,
) -> BlockResponse:
    require_tenant(context)
    try:
        return BlockResponse.from_dto(
            await service.update_block(block_id, payload.type, payload.translations)
        )
    except Exception as exc:
        raise_schema_http_error(exc)
