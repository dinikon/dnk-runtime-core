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
from src.modules.inventory.application.stock_document.command.confirm_internal_move_document.command import (
    ConfirmInternalMoveDocumentCommand,
)
from src.modules.inventory.presentation.stock_document.internal_move_depends import (
    ConfirmInternalMoveDocumentHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.confirm_internal_move_document import (
    ConfirmInternalMoveDocumentRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.confirm_internal_move_document import (
    ConfirmInternalMoveDocumentResponse,
)


async def confirm_internal_move_document(
    document_id: UUID,
    payload: ConfirmInternalMoveDocumentRequest,
    context: AuthenticatedRequestContextDep,
    handler: ConfirmInternalMoveDocumentHandlerDep,
) -> ConfirmInternalMoveDocumentResponse:
    """Преобразует собственный HTTP-контракт в намерение и явно переводит ожидаемые отказы."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ConfirmInternalMoveDocumentCommand(
                document_id=document_id,
                expected_version=payload.expected_version,
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
    return ConfirmInternalMoveDocumentResponse.from_dto(result)
