"""Транспорт сценария list_publications."""

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
from src.modules.channels.application.external_publication.query.list_publications.query import (
    ListPublicationsQuery,
)
from src.modules.channels.presentation.external_publication.depends import (
    ListPublicationsHandlerDep,
)
from src.modules.channels.presentation.external_publication.http.response.list_publications import (
    ListPublicationsResponse,
)
from src.modules.channels.presentation.external_publication.http.response.fields import (
    PublicationCardFields,
)


async def list_publications(
    channel_id: UUID,
    handler: ListPublicationsHandlerDep,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    locale: str | None = Query(default=None, max_length=8),
    binding: str = Query(default="", max_length=16),
    search: str = Query(default="", max_length=255),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> ListPublicationsResponse:
    """Проверяет доступ, вызывает Application и явно создаёт ответ."""
    tenant_id, _ = await channel_access(context, authorization, "read", channel_id)
    try:
        result = await handler.execute(
            ListPublicationsQuery(
                channel_id=channel_id,
                locale=locale,
                search=search,
                binding=binding,
                offset=offset,
                limit=limit,
            )
        )
        return ListPublicationsResponse(
            items=[PublicationCardFields.from_view(card) for card in result.items],
            total=result.total,
            offset=result.offset,
            limit=result.limit,
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
