from uuid import UUID
from src.modules.channels.application.content_update.query.list_content_updates.query import (
    ListContentUpdatesQuery,
)
from src.modules.channels.presentation.content_update.depends import (
    ListContentUpdatesHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.content_update.http.response.list_content_updates import (
    ListContentUpdatesResponse,
)
from src.modules.channels.presentation.content_update.http.response.list_content_updates import (
    ContentUpdateSummaryResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def list_content_updates(
    channel_id: UUID,
    context: CatalogLinkContextDep,
    handler: ListContentUpdatesHandlerDep,
) -> ListContentUpdatesResponse:
    """Читает проекцию операции без скрытых внешних вызовов и записей."""
    try:
        result = await handler.execute(
            ListContentUpdatesQuery(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                channel_id,
            )
        )
        return ListContentUpdatesResponse(
            items=[
                ContentUpdateSummaryResponse(
                    id=item.id,
                    status=item.status,
                    created_at=item.created_at,
                    total=item.total,
                )
                for item in result.items
            ]
        )
    except ChannelsError as error:
        raise http_error(error) from error
