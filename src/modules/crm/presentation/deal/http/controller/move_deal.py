from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import MoveDealHandlerDep
from src.modules.crm.application.deal.command.move_deal.command import MoveDealCommand
from src.modules.crm.presentation.deal.http.response.move_deal import MoveDealResponse
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.crm.presentation.deal.http.request.move_deal import MoveDealRequest


async def move_deal(
    deal_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: MoveDealHandlerDep,
    payload: MoveDealRequest,
) -> MoveDealResponse:
    """Явно преобразует HTTP move в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        result = await handler.execute(
            MoveDealCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                record_id=deal_id,
                expected_position_revision=payload.expected_position_revision,
                stage_id=payload.stage_id,
            )
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return MoveDealResponse.model_validate(asdict(result))
