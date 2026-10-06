from uuid import UUID
from fastapi import Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import UpdateChannelHandlerDep
from src.modules.channels.application.command.update_channel.command import (
    UpdateChannelCommand,
)
from src.modules.channels.presentation.http.request.update_channel import (
    UpdateChannelRequest,
)
from src.modules.channels.presentation.depends import GetChannelHandlerDep
from src.modules.channels.application.query.get_channel.query import GetChannelQuery


async def update_channel(
    payload: UpdateChannelRequest,
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: UpdateChannelHandlerDep,
    reader: GetChannelHandlerDep,
):
    tenant_id, actor_id = require_channel_context(context)
    result = await handler.execute(
        UpdateChannelCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            channel_id=channel_id,
            **payload.model_dump(),
        )
    )
    return await reader.execute(GetChannelQuery(tenant_id, result))
