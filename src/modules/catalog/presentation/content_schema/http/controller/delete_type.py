from uuid import UUID

from src.modules.catalog.presentation.content_schema.depends import (
    ContentSchemaServiceDep,
)
from src.modules.catalog.presentation.content_schema.http.context import (
    require_tenant,
    raise_schema_http_error,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def delete_type(
    type_id: UUID,
    context: AuthenticatedRequestContextDep,
    service: ContentSchemaServiceDep,
) -> None:
    require_tenant(context)
    try:
        await service.delete_type(type_id)
    except Exception as exc:
        raise_schema_http_error(exc)
