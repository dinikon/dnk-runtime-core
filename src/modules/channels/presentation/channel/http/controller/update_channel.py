from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.channel.http.context import (
    require_channel_context,
)
from src.modules.channels.presentation.channel.depends import UpdateChannelHandlerDep
from src.modules.channels.application.channel.command.update_channel.command import (
    UpdateChannelCommand,
)
from src.modules.channels.presentation.channel.http.response.update_channel import (
    UpdateChannelResponse,
)
from src.modules.channels.presentation.channel.http.request.update_channel import (
    UpdateChannelRequest,
)
from src.modules.channels.application.channel.error import (
    ChannelConfigConflictError,
    ChannelSecretsUnavailableError,
    ChannelValidationError,
)
from src.modules.channels.domain.channel.error import InvalidChannelError
from src.modules.channels.domain.channel.error import ChannelNotFoundError


async def update_channel(
    payload: UpdateChannelRequest,
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: UpdateChannelHandlerDep,
) -> UpdateChannelResponse:
    """Выполняет update_channel, явно преобразуя вход, результат и ожидаемые ошибки."""
    tenant_id, actor_id = require_channel_context(context)
    try:
        result = await handler.execute(
            UpdateChannelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                channel_id=channel_id,
                name=payload.name,
                is_active=payload.is_active,
                config_version=payload.config_version,
                connection_settings=payload.connection_settings,
            )
        )
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ChannelValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=[
                {"loc": ["body", *error.path], "msg": error.message, "type": error.code}
                for error in exc.errors
            ],
        ) from None
    except ChannelConfigConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ChannelSecretsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except InvalidChannelError as exc:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["body", exc.field_name] if exc.field_name else ["body"],
                    "msg": str(exc),
                    "type": "invalid_channel",
                }
            ],
        ) from None
    return UpdateChannelResponse.from_dto(result)
