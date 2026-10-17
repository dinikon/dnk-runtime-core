from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.channel.http.context import (
    require_channel_context,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError

from src.modules.channels.presentation.publication_import_run.depends import (
    GetPublicationImportRunHandlerDep,
)
from src.modules.channels.application.publication_import_run.query.get_publication_import_run.query import (
    GetPublicationImportRunQuery,
)
from src.modules.channels.presentation.publication_import_run.http.response.get_latest_publication_import import (
    GetLatestPublicationImportResponse,
)


async def get_latest_publication_import(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetPublicationImportRunHandlerDep,
) -> GetLatestPublicationImportResponse | None:
    """Возвращает прогресс импорта текущего подключения в контексте tenant."""
    tenant_id, _ = require_channel_context(context)
    try:
        result = await handler.execute(
            GetPublicationImportRunQuery(tenant_id, channel_id, None)
        )
    except ChannelNotFoundError:
        raise HTTPException(404, "Канал не найден.") from None
    return (
        None if result is None else GetLatestPublicationImportResponse.from_dto(result)
    )
