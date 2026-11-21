from src.modules.inventory.domain.stock_document.status_change_error import (
    InvalidStatusChangeReasonError,
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
from src.modules.inventory.application.stock_document.command.update_status_change_document_lines.command import (
    UpdateStatusChangeDocumentLinesCommand,
)
from src.modules.inventory.presentation.stock_document.status_change_depends import (
    UpdateStatusChangeDocumentLinesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.patch_status_change_document import (
    PatchStatusChangeDocumentRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_status_change_document import (
    PatchStatusChangeDocumentResponse,
)
from decimal import Decimal
from src.modules.inventory.application.stock_document.command.update_status_change_document_lines.command import (
    ExistingStatusChangeLine,
    NewStatusChangeLine,
)
from src.modules.inventory.presentation.stock_document.http.request.patch_status_change_document import (
    ExistingStatusChangeLineRequest,
)


async def patch_status_change_document(
    document_id: UUID,
    payload: PatchStatusChangeDocumentRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateStatusChangeDocumentLinesHandlerDep,
) -> PatchStatusChangeDocumentResponse:
    """Преобразует собственный HTTP-контракт в намерение и явно переводит ожидаемые отказы."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateStatusChangeDocumentLinesCommand(
                document_id=document_id,
                expected_version=payload.expected_version,
                reason=payload.reason,
                target_status=payload.target_status,
                lines=(
                    tuple(
                        (
                            ExistingStatusChangeLine(
                                line.id, Decimal(line.quantity), line.uom
                            )
                            if isinstance(line, ExistingStatusChangeLineRequest)
                            else NewStatusChangeLine(
                                line.inventory_item_id, Decimal(line.quantity), line.uom
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
    except InvalidStatusChangeReasonError as exc:
        raise HTTPException(
            422,
            detail=[
                {"loc": ["body", "reason"], "msg": str(exc), "type": "value_error"}
            ],
        ) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchStatusChangeDocumentResponse.from_dto(result)
