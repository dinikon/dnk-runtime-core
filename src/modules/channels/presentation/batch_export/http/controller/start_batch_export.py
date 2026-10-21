from dataclasses import asdict
from uuid import UUID
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError

from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.batch_export.depends import (
    StartBatchExportHandlerDep,
)
from src.modules.channels.presentation.batch_export.http.request.start_batch_export import (
    StartBatchExportRequest,
)
from src.modules.channels.presentation.batch_export.http.response.start_batch_export import (
    StartBatchExportResponse,
)
from src.modules.channels.application.batch_export.command.start_batch_export.command import (
    StartBatchExportCommand,
)


async def start_batch_export(
    channel_id: UUID,
    payload: StartBatchExportRequest,
    context: CatalogLinkContextDep,
    handler: StartBatchExportHandlerDep,
) -> StartBatchExportResponse:
    """Преобразует доверенный контекст в конкретное ручное намерение."""
    try:
        result = await handler.execute(
            StartBatchExportCommand(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                channel_id,
                payload.run_id,
                payload.delivery_mode,
            )
        )
        return StartBatchExportResponse(**asdict(result))
    except ChannelsError as error:
        raise http_error(error) from error
