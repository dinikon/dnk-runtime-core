from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.command.update_connection_settings.command import (
    UpdateConnectionSettingsCommand,
)
from src.modules.channels.presentation.channel.depends import (
    UpdateConnectionSettingsHandlerDep,
)
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.request.update_connection_settings import (
    UpdateConnectionSettingsRequest,
)
from src.modules.channels.presentation.channel.http.response.update_connection_settings import (
    UpdateConnectionSettingsResponse,
)
from src.modules.channels.domain.channel.value_object.settings import (
    ConnectionSettingsVO,
)


async def update_connection_settings(
    channel_id: UUID,
    payload: UpdateConnectionSettingsRequest,
    context: ChannelsManageContextDep,
    handler: UpdateConnectionSettingsHandlerDep,
) -> UpdateConnectionSettingsResponse:
    """Преобразует HTTP update_connection_settings в отдельный Command/Query и безопасный ответ."""
    try:
        request = UpdateConnectionSettingsCommand(
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
    return UpdateConnectionSettingsResponse(**asdict(result))
