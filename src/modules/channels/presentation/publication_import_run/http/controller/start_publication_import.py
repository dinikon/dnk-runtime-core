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
    StartPublicationImportHandlerDep,
)
from src.modules.channels.application.publication_import_run.command.start_publication_import.command import (
    StartPublicationImportCommand,
)
from src.modules.channels.application.publication_import_run.error import (
    PublicationImportUnavailableError,
)
from src.modules.channels.presentation.publication_import_run.http.response.start_publication_import import (
    StartPublicationImportResponse,
)


async def start_publication_import(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: StartPublicationImportHandlerDep,
) -> StartPublicationImportResponse:
    """Ставит импорт в очередь, возвращая существующий запуск при повторном запросе."""
    tenant_id, _ = require_channel_context(context)
    try:
        result = await handler.execute(
            StartPublicationImportCommand(tenant_id, channel_id)
        )
    except ChannelNotFoundError:
        raise HTTPException(404, "Канал не найден.") from None
    except PublicationImportUnavailableError as exc:
        raise HTTPException(409, str(exc)) from None
    return StartPublicationImportResponse.from_dto(result)
