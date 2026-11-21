from decimal import Decimal
from typing import Annotated
from uuid import UUID
from fastapi import Header, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.inventory.application.stock_document.command.post_receipt.command import (
    PostReceiptCommand,
    ReceiptActualLine,
    ReceiptCostInput,
    ReceiptCostAllocationInput,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentNotFoundError,
    StockDocumentOverExecutionError,
    StockDocumentLineNotFoundError,
    StaleStockDocumentVersionError,
    StockDocumentExecutionNotAllowedError,
    InvalidStockDocumentContextError,
)
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptPostingConflictError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.domain.policy.receipt_serial_presence import (
    ReceiptSerialAlreadyPresentError,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError
from src.modules.inventory.presentation.stock_document.depends import (
    PostReceiptHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.post_receipt import (
    PostReceiptRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.post_receipt import (
    PostReceiptResponse,
)


async def post_receipt(
    document_id: UUID,
    payload: PostReceiptRequest,
    context: AuthenticatedRequestContextDep,
    handler: PostReceiptHandlerDep,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=200, pattern=r"^[!-~]+$")
    ],
) -> PostReceiptResponse:
    """Принимает одно намерение; исполнение, Ledger, позиции и событие фиксируются общим UoW."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PostReceiptCommand(
                document_id,
                payload.expected_version,
                idempotency_key,
                UUID(context.principal.user_id),
                UUID(context.principal.tenant_id),
                tuple(
                    ReceiptActualLine(
                        v.client_line_id,
                        v.document_line_id,
                        Decimal(v.quantity),
                        v.uom,
                        v.location_id,
                        v.lot_id,
                        v.serial_id,
                        v.stock_status,
                    )
                    for v in payload.lines
                ),
                tuple(
                    ReceiptCostInput(
                        Decimal(c.amount),
                        c.currency,
                        c.basis_kind,
                        c.source_system,
                        c.source_reference,
                        tuple(
                            ReceiptCostAllocationInput(
                                a.client_line_id, Decimal(a.amount)
                            )
                            for a in c.allocations
                        ),
                    )
                    for c in payload.costs
                ),
            )
        )
    except StockDocumentOverExecutionError as exc:
        raise HTTPException(
            422,
            detail={
                "code": "stock_document_line_over_execution",
                "message": str(exc),
                "document_line_id": str(exc.document_line_id.uuid),
                "requested_quantity": str(exc.requested_quantity.value),
                "remaining_quantity": str(exc.remaining_quantity.value),
                "base_uom": exc.base_uom.value,
            },
        ) from exc
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
        ReceiptPostingConflictError,
        ReceiptSerialAlreadyPresentError,
        StockPositionVersionConflictError,
        StockDocumentExecutionNotAllowedError,
        InvalidStockDocumentContextError,
    ) as exc:
        raise HTTPException(
            409, detail={"code": "receipt_posting_conflict", "message": str(exc)}
        ) from exc
    except (
        StockDocumentNotFoundError,
        StockDocumentLineNotFoundError,
        InventoryItemNotFoundError,
        WarehouseNotFoundError,
        StockLocationNotFoundError,
        StockLotNotFoundError,
        StockSerialNotFoundError,
    ) as exc:
        raise HTTPException(404, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PostReceiptResponse.from_dto(result)
