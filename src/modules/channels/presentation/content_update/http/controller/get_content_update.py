from uuid import UUID
from src.modules.channels.application.content_update.query.get_content_update.query import (
    GetContentUpdateQuery,
)
from src.modules.channels.presentation.content_update.depends import (
    GetContentUpdateHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.content_update.http.response.get_content_update import (
    GetContentUpdateResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def get_content_update(
    run_id: UUID, context: CatalogLinkContextDep, handler: GetContentUpdateHandlerDep
) -> GetContentUpdateResponse:
    """Читает проекцию операции без скрытых внешних вызовов и записей."""
    try:
        result = await handler.execute(
            GetContentUpdateQuery(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                run_id,
            )
        )
        return GetContentUpdateResponse.from_dto(result)
    except ChannelsError as error:
        raise http_error(error) from error
