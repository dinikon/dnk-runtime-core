from uuid import UUID
from fastapi import Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import CreateChannelHandlerDep
from src.modules.channels.application.command.create_channel.command import (
    CreateChannelCommand,
)
from src.modules.channels.presentation.http.request.create_channel import (
    CreateChannelRequest,
)
from src.modules.channels.presentation.depends import GetChannelHandlerDep
from src.modules.channels.application.query.get_channel.query import GetChannelQuery


async def create_channel(
    payload: CreateChannelRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateChannelHandlerDep,
    reader: GetChannelHandlerDep,
):
    tenant_id, actor_id = require_channel_context(context)
    result = await handler.execute(
        CreateChannelCommand(
            tenant_id=tenant_id, actor_id=actor_id, **payload.model_dump()
        )
    )
    return await reader.execute(GetChannelQuery(tenant_id, result))
