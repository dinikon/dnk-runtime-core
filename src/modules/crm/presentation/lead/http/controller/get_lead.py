from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import GetLeadHandlerDep
from src.modules.crm.application.lead.query.get_lead.query import GetLeadQuery
from src.modules.crm.presentation.lead.http.response.get_lead import GetLeadResponse
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error


async def get_lead(
    lead_id: UUID, context: AuthenticatedRequestContextDep, handler: GetLeadHandlerDep
) -> GetLeadResponse:
    """Явно преобразует HTTP get в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        result = await handler.execute(
            GetLeadQuery(tenant_id=tenant_id, record_id=lead_id)
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return GetLeadResponse.model_validate(
        dict(
            **asdict(result.record),
            basket=asdict(result.basket),
            points=asdict(result.points),
        )
    )
