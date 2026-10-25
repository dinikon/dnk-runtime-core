from dataclasses import asdict
from uuid import UUID
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.sales.context import sales_identity
from src.modules.crm.presentation.depends.sales import (
    GetLeadConversionContextHandlerDep,
)
from src.modules.crm.application.lead.query.get_lead_conversion_context.query import (
    GetLeadConversionContextQuery,
)
from src.modules.crm.presentation.lead.http.response.get_conversion_context import (
    GetLeadConversionContextResponse,
)
from src.modules.crm.presentation.sales.errors import sales_http_error
from src.modules.shared.domain.domain_error import DomainError


async def get_conversion_context(
    lead_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetLeadConversionContextHandlerDep,
) -> GetLeadConversionContextResponse:
    """Читает контекст, не создавая результатов и не изменяя лид."""
    tenant_id, _ = sales_identity(context)
    try:
        result = await handler.execute(
            GetLeadConversionContextQuery(tenant_id, lead_id)
        )
    except DomainError as exc:
        raise sales_http_error(exc) from exc
    return GetLeadConversionContextResponse.model_validate(
        dict(
            source_token=result.source_token,
            source=dict(
                **asdict(result.record),
                basket=asdict(result.basket),
                points=asdict(result.points),
            ),
            available_companies=[
                dict(id=c.id, legal_name=c.legal_name)
                for c in result.available_companies
            ],
            modes=result.modes,
        )
    )
