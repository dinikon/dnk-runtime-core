from src.modules.catalog.presentation.content_schema.depends import (
    ContentSchemaServiceDep,
)
from src.modules.catalog.presentation.content_schema.http.context import require_tenant
from src.modules.catalog.presentation.content_schema.http.response.product_type import (
    ProductTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_types(
    context: AuthenticatedRequestContextDep, service: ContentSchemaServiceDep
) -> list[ProductTypeResponse]:
    require_tenant(context)
    return [ProductTypeResponse.from_dto(item) for item in await service.list_types()]
