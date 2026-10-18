from uuid import UUID
from src.modules.channels.application.channel.command.archive_channel.command import (
    ArchiveChannelCommand,
)
from src.modules.channels.presentation.channel.depends import ArchiveChannelHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.request.archive_channel import (
    ArchiveChannelRequest,
)


async def archive_channel(
    channel_id: UUID,
    payload: ArchiveChannelRequest,
    context: ChannelsManageContextDep,
    handler: ArchiveChannelHandlerDep,
) -> None:
    """Преобразует HTTP archive_channel в отдельный Command/Query и безопасный ответ."""
    try:
        request = ArchiveChannelCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
            channel_id=channel_id,
            revision=payload.revision,
        )
        await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
