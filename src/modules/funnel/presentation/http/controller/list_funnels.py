from uuid import UUID
from dataclasses import asdict
from fastapi import Query
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.funnel.presentation.depends import ListFunnelsHandlerDep
from src.modules.funnel.application.query.list_funnels.query import ListFunnelsQuery
from src.modules.funnel.presentation.http.response.list_funnels import (
    ListFunnelsResponse,
)
from src.modules.funnel.presentation.http.errors import (
    funnel_identity,
    funnel_http_error,
)


async def list_funnels(
    context: AuthenticatedRequestContextDep,
    handler: ListFunnelsHandlerDep,
    model_key: str | None = Query(default=None, pattern=r"^crm\.(lead|deal)$"),
    search: str = Query(default="", max_length=150),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> ListFunnelsResponse:
    """Явно преобразует HTTP list в конкретный сценарий процесса."""
    tenant_id, actor_id = funnel_identity(context)
    try:
        result = await handler.execute(
            ListFunnelsQuery(
                tenant_id=tenant_id,
                model_key=model_key,
                search=search,
                offset=offset,
                limit=limit,
            )
        )
    except (DomainError, IntegrityError, ValueError) as exc:
        raise funnel_http_error(exc) from exc
    return ListFunnelsResponse.model_validate(asdict(result))
