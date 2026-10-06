from uuid import UUID


from src.modules.catalog.presentation.content_schema.depends import (
    ContentSchemaServiceDep,
)
from src.modules.catalog.presentation.content_schema.http.context import (
    require_tenant,
    raise_schema_http_error,
)
from src.modules.catalog.presentation.content_schema.http.response.product_type import (
    ProductTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_type(
    type_id: UUID,
    context: AuthenticatedRequestContextDep,
    service: ContentSchemaServiceDep,
) -> ProductTypeResponse:
    require_tenant(context)
    try:
        item = await service.get_type(type_id)
    except Exception as exc:
        raise_schema_http_error(exc)
    return ProductTypeResponse.from_dto(item)
