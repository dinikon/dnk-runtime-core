from uuid import UUID

from src.modules.channels.application.stock_sync.command.refresh_publication_stock.command import (
    RefreshPublicationStockCommand,
)
from src.modules.channels.presentation.stock_sync.depends import (
    RefreshPublicationStockHandlerDep,
)
from src.modules.channels.presentation.stock_sync.http.request.refresh_publication_stock import (
    RefreshPublicationStockRequest,
)
from src.modules.channels.presentation.stock_sync.http.response.refresh_publication_stock import (
    RefreshPublicationStockResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def refresh_publication_stock(
    channel_id: UUID,
    group_id: UUID,
    payload: RefreshPublicationStockRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RefreshPublicationStockHandlerDep,
) -> RefreshPublicationStockResponse:
    """Преобразует доверенный tenant и выбранные пары в отдельную команду."""
    tenant_id, _ = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        RefreshPublicationStockCommand(
            tenant_id, channel_id, group_id, payload.publication_ids
        )
    )
    return RefreshPublicationStockResponse(operation_ids=result.operation_ids)
