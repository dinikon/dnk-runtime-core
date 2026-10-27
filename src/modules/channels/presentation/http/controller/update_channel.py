from dataclasses import asdict
from uuid import UUID

from src.modules.channels.application.command.update_channel.command import (
    UpdateChannelCommand,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.error import ChannelError
from src.modules.channels.presentation.depends import UpdateChannelHandlerDep
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.channels.presentation.http.request.update_channel import (
    UpdateChannelRequest,
)
from src.modules.channels.presentation.http.response.update_channel import (
    UpdateChannelResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)


async def update_channel(
    channel_id: UUID,
    payload: UpdateChannelRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: UpdateChannelHandlerDep,
) -> UpdateChannelResponse:
    """Преобразует HTTP-запрос в конкретную команду UpdateChannel."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    try:
        result = await handler.execute(
            UpdateChannelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                channel_id=channel_id,
                expected_revision=payload.expected_revision,
                name=payload.name,
                config=(
                    payload.config.to_value() if payload.config is not None else None
                ),
                credentials=payload.credentials,
            )
        )
    except (
        ChannelError,
        ChannelInputError,
        CipherNotConfigured,
        CiphertextUnreadable,
    ) as error:
        raise channel_http_error(error) from None
    return UpdateChannelResponse.model_validate(asdict(result))
