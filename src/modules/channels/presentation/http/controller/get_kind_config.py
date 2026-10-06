from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import GetKindConfigHandlerDep
from src.modules.channels.application.query.get_kind_config.query import (
    GetKindConfigQuery,
)
from src.modules.channels.presentation.http.response.get_kind_config import (
    GetKindConfigResponse,
)
from src.modules.channels.domain.error import ChannelNotFoundError


async def get_kind_config(
    kind: str,
    context: AuthenticatedRequestContextDep,
    handler: GetKindConfigHandlerDep,
) -> GetKindConfigResponse:
    """Выполняет get_kind_config, явно преобразуя вход, результат и ожидаемые ошибки."""
    tenant_id, actor_id = require_channel_context(context)
    try:
        result = await handler.execute(
            GetKindConfigQuery(
                tenant_id=tenant_id,
                kind=kind,
            )
        )
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return GetKindConfigResponse.from_dto(result)
