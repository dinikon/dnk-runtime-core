from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import CreateLeadHandlerDep
from src.modules.crm.application.lead.command.create_lead.command import (
    CreateLeadCommand,
)
from src.modules.crm.presentation.lead.http.response.create_lead import (
    CreateLeadResponse,
)
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.crm.presentation.lead.http.request.create_lead import CreateLeadRequest


async def create_lead(
    context: AuthenticatedRequestContextDep,
    handler: CreateLeadHandlerDep,
    payload: CreateLeadRequest,
) -> CreateLeadResponse:
    """Явно преобразует HTTP create в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        result = await handler.execute(
            CreateLeadCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                title=payload.title,
                basket=payload.basket.to_values(),
                funnel_id=payload.funnel_id,
                phones=(
                    tuple(p.to_values() for p in payload.phones)
                    if payload.phones is not None
                    else None
                ),
                emails=(
                    tuple(p.to_values() for p in payload.emails)
                    if payload.emails is not None
                    else None
                ),
                locale=payload.locale,
                first_name=payload.first_name,
                last_name=payload.last_name,
                middle_name=payload.middle_name,
                company_name=payload.company_name,
                contact_id=payload.contact_id,
                company_id=payload.company_id,
                contact_overrides=frozenset(payload.model_fields_set),
            )
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return CreateLeadResponse.model_validate(asdict(result))
