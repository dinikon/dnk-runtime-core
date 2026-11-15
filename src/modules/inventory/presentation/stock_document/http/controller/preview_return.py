from src.modules.inventory.domain.stock_document.return_error import (
    StockReturnLimitError,
)
from src.modules.inventory.domain.stock_document.return_error import (
    InsufficientReturnStockError,
)
from src.modules.inventory.domain.stock_position.error import StockPositionNotFoundError
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from src.modules.shared.domain.domain_error import DomainError
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentNotFoundError,
    StockDocumentOverExecutionError,
    StockDocumentLineNotFoundError,
    StaleStockDocumentVersionError,
    StockDocumentExecutionNotAllowedError,
)
from src.modules.inventory.domain.stock_document.return_error import (
    ReturnPostingConflictError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError
from src.modules.inventory.presentation.stock_document.return_depends import (
    PreviewReturnHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.preview_return import (
    PreviewReturnRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.preview_return import (
    PreviewReturnResponse,
)


from src.modules.inventory.application.stock_document.query.preview_return.query import (
    PreviewReturnQuery,
    PreviewReturnLine,
)


async def preview_return(
    document_id: UUID,
    payload: PreviewReturnRequest,
    handler: PreviewReturnHandlerDep,
) -> PreviewReturnResponse:
    """Проверяет read-only намерение и показывает расчёт без ключа, Outbox и физических записей."""
    try:
        result = await handler.execute(
            PreviewReturnQuery(
                document_id,
                payload.expected_version,
                tuple(
                    PreviewReturnLine(
                        client_line_id=line.client_line_id,
                        document_line_id=line.document_line_id,
                        source_position_id=line.source_position_id,
                        quantity=Decimal(line.quantity),
                        uom=line.uom,
                        location_id=line.location_id,
                        stock_status=(
                            line.stock_status.value
                            if line.stock_status is not None
                            else None
                        ),
                    )
                    for line in payload.lines
                ),
            )
        )
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
    except InsufficientReturnStockError as exc:
        raise HTTPException(
            409,
            detail={
                "code": "insufficient_stock_quantity",
                "message": str(exc),
                "position_id": str(exc.position_id.uuid),
                "requested_quantity": str(exc.requested.value),
                "current_quantity": str(exc.current.value),
                "base_uom": exc.base_uom.value,
                "client_line_ids": [
                    str(line.client_line_id)
                    for line in payload.lines
                    if line.source_position_id == exc.position_id.uuid
                ],
            },
        ) from exc
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
        ReturnPostingConflictError,
        StockPositionVersionConflictError,
        StockDocumentExecutionNotAllowedError,
    ) as exc:
        raise HTTPException(
            409, detail={"code": "return_posting_conflict", "message": str(exc)}
        ) from exc
    except (
        StockDocumentNotFoundError,
        StockPositionNotFoundError,
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
    return PreviewReturnResponse.from_dto(result)
