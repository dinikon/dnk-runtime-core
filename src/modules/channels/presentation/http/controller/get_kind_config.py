from uuid import UUID
from fastapi import Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import GetKindConfigHandlerDep
from src.modules.channels.application.query.get_kind_config.query import (
    GetKindConfigQuery,
)


async def get_kind_config(
    kind: str, context: AuthenticatedRequestContextDep, handler: GetKindConfigHandlerDep
):
    tenant_id, actor_id = require_channel_context(context)
    result = await handler.execute(GetKindConfigQuery(tenant_id=tenant_id, kind=kind))
    return result
