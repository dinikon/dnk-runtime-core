from dataclasses import asdict
from uuid import UUID

from src.modules.channels.application.command.verify_connection.command import (
    VerifyConnectionCommand,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.error import ChannelError
from src.modules.channels.presentation.depends import VerifyConnectionHandlerDep
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.channels.presentation.http.response.verify_connection import (
    VerifyConnectionResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)


async def verify_connection(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: VerifyConnectionHandlerDep,
) -> VerifyConnectionResponse:
    """Преобразует HTTP-запрос в конкретную команду VerifyConnection."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    try:
        result = await handler.execute(
            VerifyConnectionCommand(
                tenant_id=tenant_id, actor_id=actor_id, channel_id=channel_id
            )
        )
    except (
        ChannelError,
        ChannelInputError,
        CipherNotConfigured,
        CiphertextUnreadable,
    ) as error:
        raise channel_http_error(error) from None
    return VerifyConnectionResponse.model_validate(asdict(result))
