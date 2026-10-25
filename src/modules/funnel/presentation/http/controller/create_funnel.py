from uuid import UUID
from dataclasses import asdict
from fastapi import Query
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.funnel.presentation.depends import CreateFunnelHandlerDep
from src.modules.funnel.application.command.create_funnel.command import (
    CreateFunnelCommand,
)
from src.modules.funnel.presentation.http.response.create_funnel import (
    CreateFunnelResponse,
)
from src.modules.funnel.presentation.http.errors import (
    funnel_identity,
    funnel_http_error,
)
from src.modules.funnel.presentation.http.request.create_funnel import (
    CreateFunnelRequest,
)
from src.modules.funnel.application.values import StageInput


async def create_funnel(
    context: AuthenticatedRequestContextDep,
    handler: CreateFunnelHandlerDep,
    payload: CreateFunnelRequest,
) -> CreateFunnelResponse:
    """Явно преобразует HTTP create в конкретный сценарий процесса."""
    tenant_id, actor_id = funnel_identity(context)
    try:
        result = await handler.execute(
            CreateFunnelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                model_key=payload.model_key,
                name=payload.name,
                stages=tuple(StageInput(**s.model_dump()) for s in payload.stages),
            )
        )
    except (DomainError, IntegrityError, ValueError) as exc:
        raise funnel_http_error(exc) from exc
    return CreateFunnelResponse.model_validate(asdict(result))
