from dataclasses import asdict

from src.modules.channels.application.command.create_channel.command import (
    CreateChannelCommand,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.error import ChannelError
from src.modules.channels.presentation.depends import CreateChannelHandlerDep
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.channels.presentation.http.request.create_channel import (
    CreateChannelRequest,
)
from src.modules.channels.presentation.http.response.create_channel import (
    CreateChannelResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)


async def create_channel(
    payload: CreateChannelRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: CreateChannelHandlerDep,
) -> CreateChannelResponse:
    """Преобразует HTTP-запрос в конкретную команду CreateChannel."""
    tenant_id, actor_id = await channel_access(context, authorization, "manage")
    try:
        result = await handler.execute(
            CreateChannelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                name=payload.name,
                platform_kind=payload.platform_kind,
                config=payload.config.to_value(),
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
    return CreateChannelResponse.model_validate(asdict(result))
