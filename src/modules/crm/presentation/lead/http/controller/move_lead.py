from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import MoveLeadHandlerDep
from src.modules.crm.application.lead.command.move_lead.command import MoveLeadCommand
from src.modules.crm.presentation.lead.http.response.move_lead import MoveLeadResponse
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.crm.presentation.lead.http.request.move_lead import MoveLeadRequest


async def move_lead(
    lead_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: MoveLeadHandlerDep,
    payload: MoveLeadRequest,
) -> MoveLeadResponse:
    """Явно преобразует HTTP move в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        result = await handler.execute(
            MoveLeadCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                record_id=lead_id,
                expected_position_revision=payload.expected_position_revision,
                stage_id=payload.stage_id,
            )
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return MoveLeadResponse.model_validate(asdict(result))
