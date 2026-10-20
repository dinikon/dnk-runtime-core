from uuid import UUID
from src.modules.channels.application.content_update.command.retry_content_update.command import (
    RetryContentUpdateCommand,
)
from src.modules.channels.presentation.content_update.depends import (
    RetryContentUpdateHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.content_update.http.request.retry_content_update import (
    RetryContentUpdateRequest,
)
from src.modules.channels.presentation.content_update.http.response.retry_content_update import (
    RetryContentUpdateResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def retry_content_update(
    run_id: UUID,
    payload: RetryContentUpdateRequest,
    context: CatalogLinkContextDep,
    handler: RetryContentUpdateHandlerDep,
) -> RetryContentUpdateResponse:
    """Преобразует доверенный контекст и конкретный request в Command."""
    try:
        result = await handler.execute(
            RetryContentUpdateCommand(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                run_id,
                payload.expected_revision,
            )
        )
        return RetryContentUpdateResponse(run_id=result.run_id)
    except ChannelsError as error:
        raise http_error(error) from error
