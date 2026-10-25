from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import CreateDealHandlerDep
from src.modules.crm.application.deal.command.create_deal.command import (
    CreateDealCommand,
)
from src.modules.crm.presentation.deal.http.response.create_deal import (
    CreateDealResponse,
)
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.crm.presentation.deal.http.request.create_deal import CreateDealRequest


async def create_deal(
    context: AuthenticatedRequestContextDep,
    handler: CreateDealHandlerDep,
    payload: CreateDealRequest,
) -> CreateDealResponse:
    """Явно преобразует HTTP create в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        result = await handler.execute(
            CreateDealCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                title=payload.title,
                basket=payload.basket.to_values(),
                funnel_id=payload.funnel_id,
                phones=tuple(p.to_values() for p in payload.phones),
                emails=tuple(p.to_values() for p in payload.emails),
                locale=payload.locale,
                contact_ids=payload.contact_ids,
                company_ids=payload.company_ids,
            )
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return CreateDealResponse.model_validate(asdict(result))
