from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.channel.http.context import (
    require_channel_context,
)
from src.modules.channels.presentation.channel.depends import CreateChannelHandlerDep
from src.modules.channels.application.channel.command.create_channel.command import (
    CreateChannelCommand,
)
from src.modules.channels.presentation.channel.http.response.create_channel import (
    CreateChannelResponse,
)
from src.modules.channels.presentation.channel.http.request.create_channel import (
    CreateChannelRequest,
)
from src.modules.channels.application.channel.error import (
    ChannelConfigConflictError,
    ChannelSecretsUnavailableError,
    ChannelValidationError,
)
from src.modules.channels.domain.channel.error import InvalidChannelError
from src.modules.channels.domain.channel.error import ChannelNotFoundError


async def create_channel(
    payload: CreateChannelRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateChannelHandlerDep,
) -> CreateChannelResponse:
    """Выполняет create_channel, явно преобразуя вход, результат и ожидаемые ошибки."""
    tenant_id, actor_id = require_channel_context(context)
    try:
        result = await handler.execute(
            CreateChannelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                name=payload.name,
                kind=payload.kind,
                config_version=payload.config_version,
                connection_settings=payload.connection_settings,
                is_active=payload.is_active,
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
    return CreateChannelResponse.from_dto(result)
