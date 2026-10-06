from uuid import UUID
from fastapi import HTTPException, Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import DeleteChannelHandlerDep
from src.modules.channels.application.command.delete_channel.command import (
    DeleteChannelCommand,
)
from src.modules.channels.domain.error import ChannelNotFoundError


async def delete_channel(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteChannelHandlerDep,
) -> Response:
    """Выполняет delete_channel, явно преобразуя вход, результат и ожидаемые ошибки."""
    tenant_id, actor_id = require_channel_context(context)
    try:
        await handler.execute(
            DeleteChannelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                channel_id=channel_id,
            )
        )
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return Response(status_code=204)
