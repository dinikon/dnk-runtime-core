from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.external_publication.query.get_external_publication.query import (
    GetExternalPublicationQuery,
)
from src.modules.channels.presentation.external_publication.depends import (
    GetExternalPublicationHandlerDep,
)
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.external_publication.http.response.get_external_publication import (
    GetExternalPublicationResponse,
)


async def get_external_publication(
    publication_id: UUID,
    context: ChannelsReadContextDep,
    handler: GetExternalPublicationHandlerDep,
) -> GetExternalPublicationResponse:
    """Преобразует HTTP get_external_publication в отдельный Command/Query и безопасный ответ."""
    try:
        request = GetExternalPublicationQuery(
            tenant_id=UUID(context.principal.tenant_id), publication_id=publication_id
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return GetExternalPublicationResponse(**asdict(result))
