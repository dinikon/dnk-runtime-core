from dataclasses import asdict
from uuid import UUID
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError

from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.batch_export.depends import (
    ResumeBatchExportHandlerDep,
)
from src.modules.channels.presentation.batch_export.http.response.resume_batch_export import (
    ResumeBatchExportResponse,
)
from src.modules.channels.application.batch_export.command.resume_batch_export.command import (
    ResumeBatchExportCommand,
)


async def resume_batch_export(
    run_id: UUID, context: CatalogLinkContextDep, handler: ResumeBatchExportHandlerDep
) -> ResumeBatchExportResponse:
    """Запрашивает восстановление шага; неопределённая отправка допускает только чтение."""
    try:
        await handler.execute(
            ResumeBatchExportCommand(UUID(context.principal.tenant_id), run_id)
        )
        return ResumeBatchExportResponse(run_id=run_id)
    except ChannelsError as error:
        raise http_error(error) from error
