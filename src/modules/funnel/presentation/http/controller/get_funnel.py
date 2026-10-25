from uuid import UUID
from dataclasses import asdict
from fastapi import Query
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.funnel.presentation.depends import GetFunnelHandlerDep
from src.modules.funnel.application.query.get_funnel.query import GetFunnelQuery
from src.modules.funnel.presentation.http.response.get_funnel import GetFunnelResponse
from src.modules.funnel.presentation.http.errors import (
    funnel_identity,
    funnel_http_error,
)


async def get_funnel(
    funnel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetFunnelHandlerDep,
) -> GetFunnelResponse:
    """Явно преобразует HTTP get в конкретный сценарий процесса."""
    tenant_id, actor_id = funnel_identity(context)
    try:
        result = await handler.execute(
            GetFunnelQuery(tenant_id=tenant_id, funnel_id=funnel_id)
        )
    except (DomainError, IntegrityError, ValueError) as exc:
        raise funnel_http_error(exc) from exc
    return GetFunnelResponse.model_validate(asdict(result))
