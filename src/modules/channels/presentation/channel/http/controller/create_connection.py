from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.command.create_connection.command import (
    CreateConnectionCommand,
)
from src.modules.channels.presentation.channel.depends import CreateConnectionHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.request.create_connection import (
    CreateConnectionRequest,
)
from src.modules.channels.presentation.channel.http.response.create_connection import (
    CreateConnectionResponse,
)
from src.modules.channels.domain.channel.value_object.settings import (
    ConnectionSettingsVO,
)


async def create_connection(
    channel_id: UUID,
    payload: CreateConnectionRequest,
    context: ChannelsManageContextDep,
    handler: CreateConnectionHandlerDep,
) -> CreateConnectionResponse:
    """Преобразует HTTP create_connection в отдельный Command/Query и безопасный ответ."""
    try:
        request = CreateConnectionCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
            channel_id=channel_id,
            revision=payload.revision,
            settings=ConnectionSettingsVO(
                payload.settings.endpoint,
                payload.settings.locales,
                payload.settings.currency,
            ),
            credentials=payload.credentials,
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return CreateConnectionResponse(**asdict(result))
