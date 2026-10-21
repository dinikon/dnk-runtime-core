from dataclasses import asdict
from uuid import UUID
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError

from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.batch_export.depends import (
    UpdateExportScheduleHandlerDep,
)
from src.modules.channels.presentation.batch_export.http.request.update_export_schedule import (
    UpdateExportScheduleRequest,
)
from src.modules.channels.presentation.batch_export.http.response.update_export_schedule import (
    UpdateExportScheduleResponse,
)
from src.modules.channels.application.export_schedule.command.update_export_schedule.command import (
    UpdateExportScheduleCommand,
)


async def update_export_schedule(
    channel_id: UUID,
    payload: UpdateExportScheduleRequest,
    context: CatalogLinkContextDep,
    handler: UpdateExportScheduleHandlerDep,
) -> UpdateExportScheduleResponse:
    """Меняет календарную policy без изменения настроек подключения."""
    try:
        return UpdateExportScheduleResponse(
            **asdict(
                await handler.execute(
                    UpdateExportScheduleCommand(
                        UUID(context.principal.tenant_id),
                        channel_id,
                        **payload.model_dump(),
                    )
                )
            )
        )
    except ChannelsError as error:
        raise http_error(error) from error
