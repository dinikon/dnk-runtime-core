from uuid import UUID
from src.modules.channels.application.channel.command.pause_connection.command import (
    PauseConnectionCommand,
)
from src.modules.channels.presentation.channel.depends import PauseConnectionHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.request.pause_connection import (
    PauseConnectionRequest,
)


async def pause_connection(
    channel_id: UUID,
    payload: PauseConnectionRequest,
    context: ChannelsManageContextDep,
    handler: PauseConnectionHandlerDep,
) -> None:
    """Преобразует HTTP pause_connection в отдельный Command/Query и безопасный ответ."""
    try:
        request = PauseConnectionCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
            channel_id=channel_id,
            revision=payload.revision,
        )
        await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
