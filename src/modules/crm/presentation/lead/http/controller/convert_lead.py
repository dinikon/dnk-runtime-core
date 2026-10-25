from dataclasses import asdict
from uuid import UUID
from fastapi import Header
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import ConvertLeadHandlerDep
from src.modules.crm.application.lead.command.convert_lead.command import (
    ConvertLeadCommand,
    ConversionContactInput,
    ConversionCompanyInput,
    ConversionDealInput,
    ConversionLinkInput,
)
from src.modules.crm.presentation.lead.http.request.convert_lead import (
    ConvertLeadRequest,
)
from src.modules.crm.presentation.lead.http.response.convert_lead import (
    ConvertLeadResponse,
)
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.shared.domain.domain_error import DomainError


async def convert_lead(
    lead_id: UUID,
    payload: ConvertLeadRequest,
    context: AuthenticatedRequestContextDep,
    handler: ConvertLeadHandlerDep,
    idempotency_key: str = Header(min_length=1, max_length=200),
) -> ConvertLeadResponse:
    """Выполняет один атомарный план с безопасным replay."""
    tenant_id, actor_id = sales_identity(context)
    command = ConvertLeadCommand(
        tenant_id=tenant_id,
        actor_id=actor_id,
        lead_id=lead_id,
        mode=payload.mode,
        expected_source_token=payload.expected_source_token,
        expected_basket_revision=payload.expected_basket_revision,
        idempotency_key=idempotency_key,
        contact_points=payload.contact_points,
        company_points=payload.company_points,
        deal_points=payload.deal_points,
        contact=(
            ConversionContactInput(**payload.contact.model_dump())
            if payload.contact
            else None
        ),
        company=(
            ConversionCompanyInput(**payload.company.model_dump())
            if payload.company
            else None
        ),
        deal=ConversionDealInput(**payload.deal.model_dump()) if payload.deal else None,
        links=tuple(ConversionLinkInput(**p.model_dump()) for p in payload.links),
    )
    try:
        result = await handler.execute(command)
    except (DomainError, IntegrityError, ValueError) as exc:
        raise sales_http_error(exc) from exc
    return ConvertLeadResponse.model_validate(asdict(result))
