from src.modules.inventory.domain.stock_document.return_error import (
    StockReturnLimitError,
    ReturnFactNotFoundError,
)
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidReturnReasonError,
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
    StockDocumentNotFoundError,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.application.stock_document.command.create_return_draft.command import (
    CreateReturnDraftCommand,
    CreateReturnDraftLine,
)
from src.modules.inventory.presentation.stock_document.return_depends import (
    CreateReturnDraftHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.request.create_return_draft import (
    CreateReturnDraftRequest,
)
from src.modules.inventory.presentation.stock_document.http.response.create_return_draft import (
    CreateReturnDraftResponse,
)


async def create_return_draft(
    payload: CreateReturnDraftRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateReturnDraftHandlerDep,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=200, pattern=r"^[!-~]+$")
    ],
) -> CreateReturnDraftResponse:
    """Принимает только план; время, UUID и состояние задаются сервером и Domain."""
    if context.principal is None or context.principal.tenant_id is None:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateReturnDraftCommand(
                origin_execution_id=payload.origin_execution_id,
                reason=payload.reason,
                lines=tuple(
                    CreateReturnDraftLine(
                        line.origin_execution_line_id, Decimal(line.quantity), line.uom
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
        StockDocumentNotFoundError,
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
    return CreateReturnDraftResponse.from_dto(result)
