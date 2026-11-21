from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.prepare_write_off.query import (
    PrepareWriteOffQuery,
)
from src.modules.inventory.presentation.stock_document.write_off_depends import (
    PrepareWriteOffHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_write_off import (
    PrepareWriteOffResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.write_off_error import (
    WriteOffFactNotFoundError,
)


async def prepare_write_off(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: PrepareWriteOffHandlerDep,
) -> PrepareWriteOffResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(PrepareWriteOffQuery(document_id))
    except (StockDocumentNotFoundError, WriteOffFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return PrepareWriteOffResponse.from_dto(result)
