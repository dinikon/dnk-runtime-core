from src.modules.catalog.presentation.content_schema.depends import (
    ContentSchemaServiceDep,
)
from src.modules.catalog.presentation.content_schema.http.context import require_tenant
from src.modules.catalog.presentation.content_schema.http.response.block import (
    BlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_blocks(
    context: AuthenticatedRequestContextDep, service: ContentSchemaServiceDep
) -> list[BlockResponse]:
    require_tenant(context)
    return [BlockResponse.from_dto(item) for item in await service.list_blocks()]
