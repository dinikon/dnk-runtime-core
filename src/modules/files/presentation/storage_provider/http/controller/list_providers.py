from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.files.presentation.storage_provider.depends import (
    ListProvidersHandlerDep,
)
from src.modules.files.application.storage_provider.query.list_providers.query import (
    ListProvidersQuery,
)
from src.modules.files.presentation.storage_provider.http.response.list_providers import (
    ListProvidersItemResponse,
)


async def list_providers(
    context: AuthenticatedRequestContextDep, handler: ListProvidersHandlerDep
) -> list[ListProvidersItemResponse]:
    """Получает доверенный tenant-контекст и явно преобразует Query DTO в HTTP."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    tenant_id = UUID(principal.tenant_id)
    result = await handler.execute(ListProvidersQuery(tenant_id=tenant_id))
    return [ListProvidersItemResponse.from_dto(item) for item in result]
