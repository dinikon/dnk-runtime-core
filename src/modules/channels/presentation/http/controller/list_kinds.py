from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.http.context import require_channel_context
from src.modules.channels.presentation.depends import ListKindsHandlerDep
from src.modules.channels.application.query.list_kinds.query import ListKindsQuery
from src.modules.channels.presentation.http.response.list_kinds import (
    ListChannelKindItemResponse,
)
from src.modules.channels.domain.error import ChannelNotFoundError


async def list_kinds(
    context: AuthenticatedRequestContextDep,
    handler: ListKindsHandlerDep,
) -> list[ListChannelKindItemResponse]:
    """Выполняет list_kinds, явно преобразуя вход, результат и ожидаемые ошибки."""
    tenant_id, actor_id = require_channel_context(context)
    try:
        result = await handler.execute(
            ListKindsQuery(
                tenant_id=tenant_id,
            )
        )
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return [ListChannelKindItemResponse.from_dto(item) for item in result]
