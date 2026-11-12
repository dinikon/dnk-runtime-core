from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.uom.query.list_uoms.query import ListUomsQuery
from src.modules.inventory.presentation.uom.depends import ListUomsHandlerDep
from src.modules.inventory.presentation.uom.http.response.list_uoms import (
    ListUomsResponse,
)


async def list_uoms(
    context: AuthenticatedRequestContextDep, handler: ListUomsHandlerDep
) -> ListUomsResponse:
    """Возвращает разрешённые единицы пользователю консоли с tenant-контекстом."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    return ListUomsResponse.from_dto(await handler.execute(ListUomsQuery()))
