from src.modules.inventory.domain.stock_document.return_error import (
    StockReturnLimitError,
    ReturnFactNotFoundError,
)
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidReturnReasonError,
)
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
from src.modules.inventory.application.stock_document.command.update_return_document_lines.command import (
    UpdateReturnDocumentLinesCommand,
)
from src.modules.inventory.presentation.stock_document.return_depends import (
    UpdateReturnDocumentLinesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.patch_return_document import (
    PatchReturnDocumentRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_return_document import (
    PatchReturnDocumentResponse,
)
from decimal import Decimal
from src.modules.inventory.application.stock_document.command.update_return_document_lines.command import (
    ExistingReturnLine,
    NewReturnLine,
)
from src.modules.inventory.presentation.stock_document.http.request.patch_return_document import (
    ExistingReturnLineRequest,
)


async def patch_return_document(
    document_id: UUID,
    payload: PatchReturnDocumentRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateReturnDocumentLinesHandlerDep,
) -> PatchReturnDocumentResponse:
    """Преобразует собственный HTTP-контракт в намерение и явно переводит ожидаемые отказы."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateReturnDocumentLinesCommand(
                document_id=document_id,
                expected_version=payload.expected_version,
                reason=payload.reason,
                lines=(
                    tuple(
                        (
                            ExistingReturnLine(
                                line.id, Decimal(line.quantity), line.uom
                            )
                            if isinstance(line, ExistingReturnLineRequest)
                            else NewReturnLine(
                                line.origin_execution_line_id,
                                Decimal(line.quantity),
                                line.uom,
                            )
                        )
                        for line in payload.lines
                    )
                    if payload.lines is not None
                    else None
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
    except InvalidReturnReasonError as exc:
        raise HTTPException(
            422,
            detail=[
                {"loc": ["body", "reason"], "msg": str(exc), "type": "value_error"}
            ],
        ) from exc
    except StockReturnLimitError as exc:
        raise HTTPException(
            409,
            detail={
                "code": "stock_return_limit_exceeded",
                "message": str(exc),
                "origin_execution_line_id": str(exc.origin_line_id.uuid),
                "requested_quantity": str(exc.requested.value),
                "remaining_quantity": str(exc.remaining.value),
            },
        ) from exc
    except ReturnFactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchReturnDocumentResponse.from_dto(result)
