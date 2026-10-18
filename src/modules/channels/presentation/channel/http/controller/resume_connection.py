from uuid import UUID
from src.modules.channels.application.channel.command.resume_connection.command import (
    ResumeConnectionCommand,
)
from src.modules.channels.presentation.channel.depends import ResumeConnectionHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.request.resume_connection import (
    ResumeConnectionRequest,
)


async def resume_connection(
    channel_id: UUID,
    payload: ResumeConnectionRequest,
    context: ChannelsManageContextDep,
    handler: ResumeConnectionHandlerDep,
) -> None:
    """Преобразует HTTP resume_connection в отдельный Command/Query и безопасный ответ."""
    try:
        request = ResumeConnectionCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
            channel_id=channel_id,
            revision=payload.revision,
        )
        await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
