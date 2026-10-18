from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.command.update_channel_policy.command import (
    UpdateChannelPolicyCommand,
)
from src.modules.channels.presentation.channel.depends import (
    UpdateChannelPolicyHandlerDep,
)
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.request.update_channel_policy import (
    UpdateChannelPolicyRequest,
)
from src.modules.channels.presentation.channel.http.response.update_channel_policy import (
    UpdateChannelPolicyResponse,
)


async def update_channel_policy(
    channel_id: UUID,
    payload: UpdateChannelPolicyRequest,
    context: ChannelsManageContextDep,
    handler: UpdateChannelPolicyHandlerDep,
) -> UpdateChannelPolicyResponse:
    """Преобразует HTTP update_channel_policy в отдельный Command/Query и безопасный ответ."""
    try:
        request = UpdateChannelPolicyCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
            channel_id=channel_id,
            name=payload.name,
            is_enabled=payload.is_enabled,
            revision=payload.revision,
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return UpdateChannelPolicyResponse(**asdict(result))
