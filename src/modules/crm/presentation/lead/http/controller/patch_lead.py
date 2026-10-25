from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import UpdateLeadHandlerDep
from src.modules.crm.application.lead.command.update_lead.command import (
    UpdateLeadCommand,
)
from src.modules.crm.presentation.lead.http.response.patch_lead import PatchLeadResponse
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.crm.presentation.lead.http.request.patch_lead import PatchLeadRequest


async def patch_lead(
    lead_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: UpdateLeadHandlerDep,
    payload: PatchLeadRequest,
) -> PatchLeadResponse:
    """Явно преобразует HTTP patch в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        fields = {
            k: getattr(payload, k)
            for k in (
                "title",
                "first_name",
                "last_name",
                "middle_name",
                "company_name",
                "contact_id",
                "company_id",
            )
            if k in payload.model_fields_set
        }
        result = await handler.execute(
            UpdateLeadCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                record_id=lead_id,
                fields=fields,
                basket=payload.basket.to_values() if payload.basket else None,
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
            )
        )
    except (DomainError, IntegrityError, ValueError, ArithmeticError) as exc:
        raise sales_http_error(exc) from exc
    return PatchLeadResponse.model_validate(asdict(result))
