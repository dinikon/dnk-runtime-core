"""Транспорт сценария start_sync_run."""

from uuid import UUID


from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import channel_access
from src.modules.channels.presentation.http.publication_errors import (
    publication_http_error,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.channel.error import ChannelError
from src.modules.channels.domain.sync_run.error import SyncRunError
from src.modules.channels.domain.external_publication.error import (
    ExternalPublicationError,
)
from src.modules.channels.application.sync_run.command.start_sync_run.command import (
    StartSyncRunCommand,
)
from src.modules.channels.presentation.sync_run.depends import StartSyncRunHandlerDep
from src.modules.channels.presentation.sync_run.http.response.start_sync_run import (
    StartSyncRunResponse,
)


async def start_sync_run(
    channel_id: UUID,
    handler: StartSyncRunHandlerDep,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> StartSyncRunResponse:
    """Проверяет доступ, вызывает Application и явно создаёт ответ."""
    tenant_id, _ = await channel_access(context, authorization, "update", channel_id)
    try:
        result = await handler.execute(
            StartSyncRunCommand(tenant_id=tenant_id, channel_id=channel_id)
        )
        return StartSyncRunResponse(id=result.id, status=result.status)
    except (
        ChannelError,
        ChannelInputError,
        SyncRunError,
        ExternalPublicationError,
    ) as error:
        raise publication_http_error(error) from None
