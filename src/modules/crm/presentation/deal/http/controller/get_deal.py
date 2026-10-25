from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import GetDealHandlerDep
from src.modules.crm.application.deal.query.get_deal.query import GetDealQuery
from src.modules.crm.presentation.deal.http.response.get_deal import GetDealResponse
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error


async def get_deal(
    deal_id: UUID, context: AuthenticatedRequestContextDep, handler: GetDealHandlerDep
) -> GetDealResponse:
    """Явно преобразует HTTP get в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        result = await handler.execute(
            GetDealQuery(tenant_id=tenant_id, record_id=deal_id)
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return GetDealResponse.model_validate(
        dict(
            **asdict(result.record),
            basket=asdict(result.basket),
            points=asdict(result.points),
        )
    )
