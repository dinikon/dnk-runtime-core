from src.modules.inventory.domain.stock_document.issue_error import (
    InsufficientIssueStockError,
)
from src.modules.inventory.domain.stock_position.error import StockPositionNotFoundError
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from fastapi import Header, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.inventory.application.stock_document.command.post_issue.command import (
    PostIssueCommand,
    IssueActualLine,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentNotFoundError,
    StockDocumentOverExecutionError,
    StockDocumentLineNotFoundError,
    StaleStockDocumentVersionError,
    StockDocumentExecutionNotAllowedError,
)
from src.modules.inventory.domain.stock_document.issue_error import (
    IssuePostingConflictError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError
from src.modules.inventory.presentation.stock_document.issue_depends import (
    PostIssueHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.post_issue import (
    PostIssueRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.post_issue import (
    PostIssueResponse,
)


async def post_issue(
    document_id: UUID,
    payload: PostIssueRequest,
    context: AuthenticatedRequestContextDep,
    handler: PostIssueHandlerDep,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=200, pattern=r"^[!-~]+$")
    ],
) -> PostIssueResponse:
    """Принимает одно намерение; исполнение, Ledger, позиции и событие фиксируются общим UoW."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PostIssueCommand(
                document_id,
                payload.expected_version,
                idempotency_key,
                UUID(context.principal.user_id),
                UUID(context.principal.tenant_id),
                tuple(
                    IssueActualLine(
                        v.client_line_id,
                        v.document_line_id,
                        v.source_position_id,
                        Decimal(v.quantity),
                        v.uom,
                    )
                    for v in payload.lines
                ),
            )
        )
    except InsufficientIssueStockError as exc:
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
        IssuePostingConflictError,
        StockPositionVersionConflictError,
        StockDocumentExecutionNotAllowedError,
    ) as exc:
        raise HTTPException(
            409, detail={"code": "issue_posting_conflict", "message": str(exc)}
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
    return PostIssueResponse.from_dto(result)
