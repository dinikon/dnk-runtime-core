from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.sync_run.query.get_publication_initialization.query import (
    GetPublicationInitializationQuery,
)
from src.modules.channels.presentation.sync_run.depends import (
    GetPublicationInitializationHandlerDep,
)
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.sync_run.http.response.get_publication_initialization import (
    GetPublicationInitializationResponse,
)


async def get_publication_initialization(
    connection_id: UUID,
    context: ChannelsReadContextDep,
    handler: GetPublicationInitializationHandlerDep,
) -> GetPublicationInitializationResponse:
    """Преобразует HTTP get_publication_initialization в отдельный Command/Query и безопасный ответ."""
    try:
        request = GetPublicationInitializationQuery(
            tenant_id=UUID(context.principal.tenant_id), connection_id=connection_id
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return GetPublicationInitializationResponse(**asdict(result))
