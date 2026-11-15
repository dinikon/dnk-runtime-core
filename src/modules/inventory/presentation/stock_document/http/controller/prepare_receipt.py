from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_document.query.prepare_receipt.query import (
    PrepareReceiptQuery,
)
from src.modules.inventory.presentation.stock_document.depends import (
    PrepareReceiptHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_receipt import (
    PrepareReceiptResponse,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)


async def prepare_receipt(
    document_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: PrepareReceiptHandlerDep,
) -> PrepareReceiptResponse:
    """Читает собственный сценарий в доверенном tenant-контексте."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(PrepareReceiptQuery(document_id))
    except (StockDocumentNotFoundError, ReceiptFactNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return PrepareReceiptResponse.from_dto(result)
