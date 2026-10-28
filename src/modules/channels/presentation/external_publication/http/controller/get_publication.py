"""Транспорт сценария get_publication."""

from uuid import UUID

from fastapi import Query

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
from src.modules.channels.application.external_publication.query.get_publication.query import (
    GetPublicationQuery,
)
from src.modules.channels.presentation.external_publication.depends import (
    GetPublicationHandlerDep,
)
from src.modules.channels.presentation.external_publication.http.response.get_publication import (
    GetPublicationResponse,
)
from src.modules.channels.presentation.external_publication.http.response.fields import (
    PublicationCardFields,
)


async def get_publication(
    channel_id: UUID,
    handler: GetPublicationHandlerDep,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    publication_id: UUID,
    locale: str | None = Query(default=None, max_length=8),
) -> GetPublicationResponse:
    """Проверяет доступ, вызывает Application и явно создаёт ответ."""
    tenant_id, _ = await channel_access(context, authorization, "read", channel_id)
    try:
        result = await handler.execute(
            GetPublicationQuery(
                channel_id=channel_id, locale=locale, publication_id=publication_id
            )
        )
        return GetPublicationResponse(
            card=PublicationCardFields.from_view(result.card),
            locale=result.locale,
            locales=list(result.locales),
        )
    except (
        ChannelError,
        ChannelInputError,
        SyncRunError,
        ExternalPublicationError,
    ) as error:
        raise publication_http_error(error) from None
