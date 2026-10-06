from uuid import UUID
from fastapi import Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import ListKindsHandlerDep
from src.modules.channels.application.query.list_kinds.query import ListKindsQuery


async def list_kinds(
    context: AuthenticatedRequestContextDep, handler: ListKindsHandlerDep
):
    tenant_id, actor_id = require_channel_context(context)
    result = await handler.execute(ListKindsQuery(tenant_id=tenant_id))
    return result
