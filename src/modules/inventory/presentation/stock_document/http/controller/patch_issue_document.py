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
from src.modules.inventory.application.stock_document.command.update_issue_document_lines.command import (
    UpdateIssueDocumentLinesCommand,
)
from src.modules.inventory.presentation.stock_document.issue_depends import (
    UpdateIssueDocumentLinesHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.patch_issue_document import (
    PatchIssueDocumentRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_issue_document import (
    PatchIssueDocumentResponse,
)
from decimal import Decimal
from src.modules.inventory.application.stock_document.command.update_issue_document_lines.command import (
    ExistingIssueLine,
    NewIssueLine,
)
from src.modules.inventory.presentation.stock_document.http.request.patch_issue_document import (
    ExistingIssueLineRequest,
)


async def patch_issue_document(
    document_id: UUID,
    payload: PatchIssueDocumentRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateIssueDocumentLinesHandlerDep,
) -> PatchIssueDocumentResponse:
    """Преобразует собственный HTTP-контракт в намерение и явно переводит ожидаемые отказы."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateIssueDocumentLinesCommand(
                document_id=document_id,
                expected_version=payload.expected_version,
                lines=tuple(
                    (
                        ExistingIssueLine(line.id, Decimal(line.quantity), line.uom)
                        if isinstance(line, ExistingIssueLineRequest)
                        else NewIssueLine(
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
    return PatchIssueDocumentResponse.from_dto(result)
