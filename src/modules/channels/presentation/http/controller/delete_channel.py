from uuid import UUID
from fastapi import Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import DeleteChannelHandlerDep
from src.modules.channels.application.command.delete_channel.command import (
    DeleteChannelCommand,
)


async def delete_channel(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteChannelHandlerDep,
):
    tenant_id, actor_id = require_channel_context(context)
    result = await handler.execute(
        DeleteChannelCommand(
            tenant_id=tenant_id, actor_id=actor_id, channel_id=channel_id
        )
    )
    return Response(status_code=204)
