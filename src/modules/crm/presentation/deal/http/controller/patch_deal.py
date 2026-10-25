from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import UpdateDealHandlerDep
from src.modules.crm.application.deal.command.update_deal.command import (
    UpdateDealCommand,
)
from src.modules.crm.presentation.deal.http.response.patch_deal import PatchDealResponse
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.crm.presentation.deal.http.request.patch_deal import PatchDealRequest


async def patch_deal(
    deal_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: UpdateDealHandlerDep,
    payload: PatchDealRequest,
) -> PatchDealResponse:
    """Явно преобразует HTTP patch в конкретный сценарий и собственный Response."""
    tenant_id, actor_id = sales_identity(context)
    try:
        fields = {
            k: getattr(payload, k)
            for k in ("title", "contact_ids", "company_ids")
            if k in payload.model_fields_set
        }
        result = await handler.execute(
            UpdateDealCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                record_id=deal_id,
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
    return PatchDealResponse.model_validate(asdict(result))
