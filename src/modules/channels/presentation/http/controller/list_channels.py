from uuid import UUID
from fastapi import Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import ListChannelsHandlerDep
from src.modules.channels.application.query.list_channels.query import ListChannelsQuery


async def list_channels(
    context: AuthenticatedRequestContextDep, handler: ListChannelsHandlerDep
):
    tenant_id, actor_id = require_channel_context(context)
    result = await handler.execute(ListChannelsQuery(tenant_id=tenant_id))
    return result
