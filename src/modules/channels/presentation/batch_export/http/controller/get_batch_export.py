from dataclasses import asdict
from uuid import UUID
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError

from fastapi import Query, Response
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.batch_export.depends import (
    GetBatchExportHandlerDep,
)
from src.modules.channels.presentation.batch_export.http.response.get_batch_export import (
    GetBatchExportResponse,
)
from src.modules.channels.application.batch_export.query.get_batch_export.query import (
    GetBatchExportQuery,
)


async def get_batch_export(
    run_id: UUID,
    context: ChannelsReadContextDep,
    handler: GetBatchExportHandlerDep,
    response: Response,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> GetBatchExportResponse:
    """Возвращает страницу результатов только текущего tenant."""
    try:
        response.headers["Cache-Control"] = "no-store"
        return GetBatchExportResponse(
            **asdict(
                await handler.execute(
                    GetBatchExportQuery(
                        UUID(context.principal.tenant_id), run_id, offset, limit
                    )
                )
            )
        )
    except ChannelsError as error:
        raise http_error(error) from error
