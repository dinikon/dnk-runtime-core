"""Транспорт сценария get_sync_run."""

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
from src.modules.channels.application.sync_run.query.get_sync_run.query import (
    GetSyncRunQuery,
)
from src.modules.channels.presentation.sync_run.depends import GetSyncRunHandlerDep
from src.modules.channels.presentation.sync_run.http.response.get_sync_run import (
    GetSyncRunResponse,
)
from src.modules.channels.presentation.sync_run.http.response.fields import (
    SyncRunFields,
)


async def get_sync_run(
    channel_id: UUID,
    handler: GetSyncRunHandlerDep,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    run_id: UUID,
) -> GetSyncRunResponse:
    """Проверяет доступ, вызывает Application и явно создаёт ответ."""
    tenant_id, _ = await channel_access(context, authorization, "read", channel_id)
    try:
        result = await handler.execute(
            GetSyncRunQuery(tenant_id=tenant_id, channel_id=channel_id, run_id=run_id)
        )
        return GetSyncRunResponse(sync_run=SyncRunFields.from_row(result.sync_run))
    except (
        ChannelError,
        ChannelInputError,
        SyncRunError,
        ExternalPublicationError,
    ) as error:
        raise publication_http_error(error) from None
