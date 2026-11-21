from src.modules.inventory.domain.stock_document.status_change_error import (
    InvalidStatusChangeReasonError,
)
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
from src.modules.inventory.application.stock_document.command.create_status_change_draft.command import (
    CreateStatusChangeDraftCommand,
    CreateStatusChangeDraftLine,
)
from src.modules.inventory.presentation.stock_document.status_change_depends import (
    CreateStatusChangeDraftHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.create_status_change_draft import (
    CreateStatusChangeDraftRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.create_status_change_draft import (
    CreateStatusChangeDraftResponse,
)


async def create_status_change_draft(
    payload: CreateStatusChangeDraftRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateStatusChangeDraftHandlerDep,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=200, pattern=r"^[!-~]+$")
    ],
) -> CreateStatusChangeDraftResponse:
    """Принимает только план; время, UUID и состояние задаются сервером и Domain."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateStatusChangeDraftCommand(
                warehouse_id=payload.warehouse_id,
                reason=payload.reason,
                target_status=payload.target_status,
                owner_id=payload.owner_id,
                lines=tuple(
                    CreateStatusChangeDraftLine(
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
    except InvalidStatusChangeReasonError as exc:
        raise HTTPException(
            422,
            detail=[
                {"loc": ["body", "reason"], "msg": str(exc), "type": "value_error"}
            ],
        ) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateStatusChangeDraftResponse.from_dto(result)
