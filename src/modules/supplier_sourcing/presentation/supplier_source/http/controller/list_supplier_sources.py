from typing import Annotated
from fastapi import HTTPException, Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.supplier_sourcing.presentation.supplier_source.depends import (
    ListSupplierSourcesHandlerDep,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.request.list_supplier_sources import (
    ListSupplierSourcesRequest,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.list_supplier_sources import (
    ListSupplierSourcesResponse,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.query import (
    ListSupplierSourcesQuery,
)


async def list_supplier_sources(
    context: AuthenticatedRequestContextDep,
    handler: ListSupplierSourcesHandlerDep,
    filters: Annotated[ListSupplierSourcesRequest, Query()],
) -> ListSupplierSourcesResponse:
    """Передаёт проверенные фильтры с составной ссылкой в сценарий списка."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(
        ListSupplierSourcesQuery(
            search=filters.search,
            supplier_model_key=filters.supplier_model_key,
            supplier_id=filters.supplier_id,
            is_active=filters.is_active,
            fulfillment_mode=filters.fulfillment_mode,
            offset=filters.offset,
            limit=filters.limit,
        )
    )
    return ListSupplierSourcesResponse.from_dto(result)
