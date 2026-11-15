from src.modules.inventory.domain.stock_document.return_error import (
    StockReturnLimitError,
    ReturnFactNotFoundError,
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
from src.modules.inventory.application.stock_document.command.confirm_return_document.command import (
    ConfirmReturnDocumentCommand,
)
from src.modules.inventory.presentation.stock_document.return_depends import (
    ConfirmReturnDocumentHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.confirm_return_document import (
    ConfirmReturnDocumentRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.confirm_return_document import (
    ConfirmReturnDocumentResponse,
)


async def confirm_return_document(
    document_id: UUID,
    payload: ConfirmReturnDocumentRequest,
    context: AuthenticatedRequestContextDep,
    handler: ConfirmReturnDocumentHandlerDep,
) -> ConfirmReturnDocumentResponse:
    """Преобразует собственный HTTP-контракт в намерение и явно переводит ожидаемые отказы."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ConfirmReturnDocumentCommand(
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
    return ConfirmReturnDocumentResponse.from_dto(result)
