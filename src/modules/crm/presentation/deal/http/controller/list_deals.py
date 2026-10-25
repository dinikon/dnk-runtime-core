from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import ListDealsHandlerDep
from src.modules.crm.application.deal.query.list_deals.query import ListDealsQuery
from src.modules.crm.presentation.deal.http.response.list_deal import ListDealsResponse
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error


async def list_deals(
    context: AuthenticatedRequestContextDep,
    handler: ListDealsHandlerDep,
    funnel_id: UUID | None = None,
    stage_id: UUID | None = None,
    search: str = Query(default="", max_length=255),
    converted: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="updated", pattern="^(updated|title)$"),
) -> ListDealsResponse:
    """Явно преобразует HTTP list в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        result = await handler.execute(
            ListDealsQuery(
                tenant_id=tenant_id,
                funnel_id=funnel_id,
                stage_id=stage_id,
                search=search,
                converted=converted,
                offset=offset,
                limit=limit,
                sort=sort,
            )
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return ListDealsResponse.model_validate(
        dict(
            items=[
                dict(**asdict(i.record), basket=asdict(i.basket)) for i in result.items
            ],
            total=result.total,
            offset=result.offset,
            limit=result.limit,
        )
    )
