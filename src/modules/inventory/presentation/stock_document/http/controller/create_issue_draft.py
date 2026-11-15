from decimal import Decimal
from typing import Annotated
from uuid import UUID
from fastapi import Header, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentCreationConflictError,
    StockDocumentLineCreationError,
    StockDocumentOwnerNotFoundError,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.application.stock_document.command.create_issue_draft.command import (
    CreateIssueDraftCommand,
    CreateIssueDraftLine,
)
from src.modules.inventory.presentation.stock_document.issue_depends import (
    CreateIssueDraftHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.create_issue_draft import (
    CreateIssueDraftRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.create_issue_draft import (
    CreateIssueDraftResponse,
)


async def create_issue_draft(
    payload: CreateIssueDraftRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateIssueDraftHandlerDep,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=200, pattern=r"^[!-~]+$")
    ],
) -> CreateIssueDraftResponse:
    """Принимает только план; время, UUID и состояние задаются сервером и Domain."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateIssueDraftCommand(
                warehouse_id=payload.warehouse_id,
                owner_id=payload.owner_id,
                lines=tuple(
                    CreateIssueDraftLine(
                        line.inventory_item_id, Decimal(line.quantity), line.uom
                    )
                    for line in payload.lines
                ),
                actor_id=UUID(context.principal.user_id),
                idempotency_key=idempotency_key,
            )
        )
    except StockDocumentCreationConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (
        StockDocumentOwnerNotFoundError,
        InventoryItemNotFoundError,
        WarehouseNotFoundError,
    ) as exc:
        raise HTTPException(404, str(exc)) from exc
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
    return CreateIssueDraftResponse.from_dto(result)
