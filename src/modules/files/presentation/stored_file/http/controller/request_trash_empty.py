from uuid import UUID
from src.modules.files.application.stored_file.command.request_trash_empty.command import (
    RequestTrashEmptyCommand,
)
from src.modules.files.presentation.depends.admin import FilesEmptyTrashContextDep
from src.modules.files.presentation.stored_file.depends import (
    RequestTrashEmptyHandlerDep,
)
from src.modules.files.presentation.stored_file.http.response.request_trash_empty import (
    RequestTrashEmptyResponse,
)


async def request_trash_empty(
    context: FilesEmptyTrashContextDep,
    handler: RequestTrashEmptyHandlerDep,
) -> RequestTrashEmptyResponse:
    """Преобразует доверенный principal в запрос очистки без тела и клиентских фильтров."""
    assert context.principal is not None and context.principal.tenant_id is not None
    result = await handler.execute(
        RequestTrashEmptyCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
        )
    )
    return RequestTrashEmptyResponse.from_dto(result)
