from uuid import UUID

from src.modules.channels.application.stock_sync.command.export_catalog_stock.command import (
    ExportCatalogStockCommand,
)
from src.modules.channels.presentation.stock_sync.depends import (
    ExportCatalogStockHandlerDep,
)
from src.modules.channels.presentation.stock_sync.http.request.export_catalog_stock import (
    ExportCatalogStockRequest,
)
from src.modules.channels.presentation.stock_sync.http.response.export_catalog_stock import (
    ExportCatalogStockResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def export_catalog_stock(
    channel_id: UUID,
    group_id: UUID,
    payload: ExportCatalogStockRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ExportCatalogStockHandlerDep,
) -> ExportCatalogStockResponse:
    """Преобразует доверенный tenant и выбранные пары в отдельную команду."""
    tenant_id, _ = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        ExportCatalogStockCommand(
            tenant_id, channel_id, group_id, payload.publication_ids
        )
    )
    return ExportCatalogStockResponse(operation_ids=result.operation_ids)
