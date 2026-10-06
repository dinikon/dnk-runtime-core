from uuid import UUID
from fastapi import Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import GetChannelHandlerDep
from src.modules.channels.application.query.get_channel.query import GetChannelQuery


async def get_channel(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetChannelHandlerDep,
):
    tenant_id, actor_id = require_channel_context(context)
    result = await handler.execute(
        GetChannelQuery(tenant_id=tenant_id, channel_id=channel_id)
    )
    return result
