from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.inventory.domain.stock_document.error import (
    StaleStockDocumentVersionError,
    StockDocumentNotFoundError,
    StockDocumentLineNotFoundError,
    StockDocumentNotDraftError,
    InvalidStockDocumentContextError,
    StockDocumentLineCreationError,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.application.stock_document.command.update_receipt_document_lines.command import (
    UpdateReceiptDocumentLinesCommand,
)
from src.modules.inventory.presentation.stock_document.depends import (
    UpdateReceiptDocumentLinesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.patch_receipt_document import (
    PatchReceiptDocumentRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_receipt_document import (
    PatchReceiptDocumentResponse,
)
from decimal import Decimal
from src.modules.inventory.application.stock_document.command.update_receipt_document_lines.command import (
    ExistingReceiptLine,
    NewReceiptLine,
)
from src.modules.inventory.presentation.stock_document.http.request.patch_receipt_document import (
    ExistingReceiptLineRequest,
)


async def patch_receipt_document(
    document_id: UUID,
    payload: PatchReceiptDocumentRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateReceiptDocumentLinesHandlerDep,
) -> PatchReceiptDocumentResponse:
    """Преобразует собственный HTTP-контракт в намерение и явно переводит ожидаемые отказы."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateReceiptDocumentLinesCommand(
                document_id=document_id,
                expected_version=payload.expected_version,
                lines=tuple(
                    (
                        ExistingReceiptLine(line.id, Decimal(line.quantity), line.uom)
                        if isinstance(line, ExistingReceiptLineRequest)
                        else NewReceiptLine(
                            line.inventory_item_id, Decimal(line.quantity), line.uom
                        )
                    )
                    for line in payload.lines
                ),
            )
        )
    except StaleStockDocumentVersionError as exc:
        raise HTTPException(
            409,
            detail={
                "code": "stock_document_version_conflict",
                "message": str(exc),
                "expected_version": exc.expected_version,
                "actual_version": exc.actual_version,
            },
        ) from exc
    except (
        StockDocumentNotFoundError,
        StockDocumentLineNotFoundError,
        InventoryItemNotFoundError,
        WarehouseNotFoundError,
    ) as exc:
        raise HTTPException(404, str(exc)) from exc
    except (StockDocumentNotDraftError, InvalidStockDocumentContextError) as exc:
        raise HTTPException(
            409, detail={"code": "stock_document_state_conflict", "message": str(exc)}
        ) from exc
    except StockDocumentLineCreationError as exc:
        raise HTTPException(
            422,
            detail=[
                {
                    "loc": ["body", "lines", exc.position],
                    "msg": str(exc),
                    "type": "value_error",
                }
            ],
        ) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchReceiptDocumentResponse.from_dto(result)
