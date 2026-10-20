from uuid import UUID
from src.modules.channels.application.content_update.command.confirm_content_update.command import (
    ConfirmContentUpdateCommand,
)
from src.modules.channels.presentation.content_update.depends import (
    ConfirmContentUpdateHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.content_update.http.request.confirm_content_update import (
    ConfirmContentUpdateRequest,
)
from src.modules.channels.presentation.content_update.http.response.confirm_content_update import (
    ConfirmContentUpdateResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def confirm_content_update(
    run_id: UUID,
    payload: ConfirmContentUpdateRequest,
    context: CatalogLinkContextDep,
    handler: ConfirmContentUpdateHandlerDep,
) -> ConfirmContentUpdateResponse:
    """Преобразует доверенный контекст и конкретный request в Command."""
    try:
        result = await handler.execute(
            ConfirmContentUpdateCommand(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                run_id,
                payload.expected_revision,
                payload.preview_hash,
            )
        )
        return ConfirmContentUpdateResponse(run_id=result.run_id)
    except ChannelsError as error:
        raise http_error(error) from error
