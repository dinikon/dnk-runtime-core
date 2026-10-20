from uuid import UUID
from src.modules.channels.application.content_update.command.start_content_update.command import (
    StartContentUpdateCommand,
)
from src.modules.channels.presentation.content_update.depends import (
    StartContentUpdateHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.content_update.http.request.start_content_update import (
    StartContentUpdateRequest,
)
from src.modules.channels.presentation.content_update.http.response.start_content_update import (
    StartContentUpdateResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def start_content_update(
    channel_id: UUID,
    payload: StartContentUpdateRequest,
    context: CatalogLinkContextDep,
    handler: StartContentUpdateHandlerDep,
) -> StartContentUpdateResponse:
    """Преобразует доверенный контекст и конкретный request в Command."""
    try:
        result = await handler.execute(
            StartContentUpdateCommand(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                channel_id,
                payload.run_id,
                tuple(payload.publication_ids),
            )
        )
        return StartContentUpdateResponse(run_id=result.run_id)
    except ChannelsError as error:
        raise http_error(error) from error
