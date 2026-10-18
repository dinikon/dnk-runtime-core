from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.command.verify_connection.command import (
    VerifyConnectionCommand,
)
from src.modules.channels.presentation.channel.depends import VerifyConnectionHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.request.verify_connection import (
    VerifyConnectionRequest,
)
from src.modules.channels.presentation.channel.http.response.verify_connection import (
    VerifyConnectionResponse,
)


async def verify_connection(
    channel_id: UUID,
    payload: VerifyConnectionRequest,
    context: ChannelsManageContextDep,
    handler: VerifyConnectionHandlerDep,
) -> VerifyConnectionResponse:
    """Преобразует HTTP verify_connection в отдельный Command/Query и безопасный ответ."""
    try:
        request = VerifyConnectionCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
            channel_id=channel_id,
            revision=payload.revision,
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return VerifyConnectionResponse(**asdict(result))
