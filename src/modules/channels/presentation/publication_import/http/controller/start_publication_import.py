from uuid import UUID
from src.modules.channels.application.publication_import.command.start_publication_import.command import (
    StartPublicationImportCommand,
)
from src.modules.channels.presentation.publication_import.depends import (
    StartPublicationImportHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogCreateContextDep
from src.modules.channels.presentation.publication_import.http.request.start_publication_import import (
    StartPublicationImportRequest,
)
from src.modules.channels.presentation.publication_import.http.response.start_publication_import import (
    StartPublicationImportResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def start_publication_import(
    publication_id: UUID,
    payload: StartPublicationImportRequest,
    context: CatalogCreateContextDep,
    handler: StartPublicationImportHandlerDep,
) -> StartPublicationImportResponse:
    """Преобразует запрос и доверенный контекст в конкретную команду."""
    try:
        result = await handler.execute(
            StartPublicationImportCommand(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                publication_id,
                payload.preparation_id,
                payload.expected_observed_revision,
            )
        )
        return StartPublicationImportResponse(preparation_id=result.preparation_id)
    except ChannelsError as error:
        raise http_error(error) from error
