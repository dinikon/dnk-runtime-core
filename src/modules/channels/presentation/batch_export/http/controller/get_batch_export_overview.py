from dataclasses import asdict
from uuid import UUID
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError

from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.batch_export.depends import (
    GetBatchExportOverviewHandlerDep,
)
from src.modules.channels.presentation.batch_export.http.response.get_batch_export_overview import (
    GetBatchExportOverviewResponse,
)
from src.modules.channels.application.batch_export.query.get_batch_export_overview.query import (
    GetBatchExportOverviewQuery,
)


async def get_batch_export_overview(
    channel_id: UUID,
    context: ChannelsReadContextDep,
    handler: GetBatchExportOverviewHandlerDep,
) -> GetBatchExportOverviewResponse:
    """Читает настройки и историю без внешней синхронизации."""
    try:
        return GetBatchExportOverviewResponse(
            **asdict(
                await handler.execute(
                    GetBatchExportOverviewQuery(
                        channel_id, UUID(context.principal.tenant_id)
                    )
                )
            )
        )
    except ChannelsError as error:
        raise http_error(error) from error
