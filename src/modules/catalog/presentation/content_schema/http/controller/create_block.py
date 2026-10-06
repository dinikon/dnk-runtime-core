from src.modules.catalog.presentation.content_schema.depends import (
    ContentSchemaServiceDep,
)
from src.modules.catalog.presentation.content_schema.http.context import (
    require_tenant,
    raise_schema_http_error,
)
from src.modules.catalog.presentation.content_schema.http.request.create_block import (
    CreateBlockRequest,
)
from src.modules.catalog.presentation.content_schema.http.response.block import (
    BlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def create_block(
    payload: CreateBlockRequest,
    context: AuthenticatedRequestContextDep,
    service: ContentSchemaServiceDep,
) -> BlockResponse:
    require_tenant(context)
    try:
        return BlockResponse.from_dto(
            await service.create_block(payload.code, payload.type, payload.translations)
        )
    except Exception as exc:
        raise_schema_http_error(exc)
