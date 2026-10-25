from uuid import UUID
from dataclasses import asdict
from fastapi import Query
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.funnel.presentation.depends import UpdateFunnelHandlerDep
from src.modules.funnel.application.command.update_funnel.command import (
    UpdateFunnelCommand,
)
from src.modules.funnel.presentation.http.response.update_funnel import (
    UpdateFunnelResponse,
)
from src.modules.funnel.presentation.http.errors import (
    funnel_identity,
    funnel_http_error,
)
from src.modules.funnel.presentation.http.request.update_funnel import (
    UpdateFunnelRequest,
)
from src.modules.funnel.application.values import StageInput


async def update_funnel(
    funnel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: UpdateFunnelHandlerDep,
    payload: UpdateFunnelRequest,
) -> UpdateFunnelResponse:
    """Явно преобразует HTTP update в конкретный сценарий процесса."""
    tenant_id, actor_id = funnel_identity(context)
    try:
        result = await handler.execute(
            UpdateFunnelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                funnel_id=funnel_id,
                expected_revision=payload.expected_revision,
                name=payload.name,
                stages=tuple(StageInput(**s.model_dump()) for s in payload.stages),
            )
        )
    except (DomainError, IntegrityError, ValueError) as exc:
        raise funnel_http_error(exc) from exc
    return UpdateFunnelResponse.model_validate(asdict(result))
