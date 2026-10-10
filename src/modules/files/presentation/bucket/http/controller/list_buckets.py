from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.files.presentation.bucket.depends import ListBucketsHandlerDep
from src.modules.files.application.bucket.query.list_buckets.query import (
    ListBucketsQuery,
)
from src.modules.files.presentation.bucket.http.response.list_buckets import (
    ListBucketsItemResponse,
)


async def list_buckets(
    context: AuthenticatedRequestContextDep,
    handler: ListBucketsHandlerDep,
    provider_id: UUID | None = None,
) -> list[ListBucketsItemResponse]:
    """Получает доверенный tenant-контекст и явно преобразует Query DTO в HTTP."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    tenant_id = UUID(principal.tenant_id)
    result = await handler.execute(
        ListBucketsQuery(tenant_id=tenant_id, provider_id=provider_id)
    )
    return [ListBucketsItemResponse.from_dto(item) for item in result]
