from dataclasses import asdict
from uuid import UUID

from src.modules.channels.application.stock_sync.query.get_binding_stock.query import (
    GetBindingStockQuery,
)
from src.modules.channels.presentation.stock_sync.depends import (
    GetBindingStockHandlerDep,
)
from src.modules.channels.presentation.stock_sync.http.response.get_binding_stock import (
    GetBindingStockResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def get_binding_stock(
    channel_id: UUID,
    group_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetBindingStockHandlerDep,
) -> GetBindingStockResponse:
    """GET читает только локальное состояние и не обращается к площадке."""
    await channel_access(context, authorization, "read", channel_id)
    result = await handler.execute(GetBindingStockQuery(channel_id, group_id))
    return GetBindingStockResponse.model_validate(asdict(result))
