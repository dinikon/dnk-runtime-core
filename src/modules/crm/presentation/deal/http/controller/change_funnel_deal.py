from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import ChangeDealFunnelHandlerDep
from src.modules.crm.application.deal.command.change_funnel_deal.command import (
    ChangeDealFunnelCommand,
)
from src.modules.crm.presentation.deal.http.response.change_funnel_deal import (
    ChangeFunnelDealResponse,
)
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.crm.presentation.deal.http.request.change_funnel_deal import (
    ChangeFunnelDealRequest,
)


async def change_funnel_deal(
    deal_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ChangeDealFunnelHandlerDep,
    payload: ChangeFunnelDealRequest,
) -> ChangeFunnelDealResponse:
    """Явно преобразует HTTP change_funnel в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        result = await handler.execute(
            ChangeDealFunnelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                record_id=deal_id,
                expected_position_revision=payload.expected_position_revision,
                funnel_id=payload.funnel_id,
            )
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return ChangeFunnelDealResponse.model_validate(asdict(result))
