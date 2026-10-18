from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.sync_run.command.start_publication_initialization.command import (
    StartPublicationInitializationCommand,
)
from src.modules.channels.presentation.sync_run.depends import (
    StartPublicationInitializationHandlerDep,
)
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.sync_run.http.request.start_publication_initialization import (
    StartPublicationInitializationRequest,
)
from src.modules.channels.presentation.sync_run.http.response.start_publication_initialization import (
    StartPublicationInitializationResponse,
)


async def start_publication_initialization(
    connection_id: UUID,
    payload: StartPublicationInitializationRequest,
    context: ChannelsManageContextDep,
    handler: StartPublicationInitializationHandlerDep,
) -> StartPublicationInitializationResponse:
    """Преобразует HTTP start_publication_initialization в отдельный Command/Query и безопасный ответ."""
    try:
        request = StartPublicationInitializationCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
            connection_id=connection_id,
            request_key=payload.request_key,
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return StartPublicationInitializationResponse(**asdict(result))
