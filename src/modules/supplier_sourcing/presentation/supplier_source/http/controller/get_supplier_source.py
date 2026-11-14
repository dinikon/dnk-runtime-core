from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    SupplierSourceNotFoundError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)

from src.modules.supplier_sourcing.presentation.supplier_source.depends import (
    GetSupplierSourceHandlerDep,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.get_supplier_source import (
    GetSupplierSourceResponse,
)
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.query import (
    GetSupplierSourceQuery,
)


async def get_supplier_source(
    source_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetSupplierSourceHandlerDep,
) -> GetSupplierSourceResponse:
    """Читает карточку источника в доверенном tenant-контексте."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetSupplierSourceQuery(SupplierSourceIdVO.from_value(source_id))
        )
    except SupplierSourceNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetSupplierSourceResponse.from_dto(result)
