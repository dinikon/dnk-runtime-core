from uuid import UUID
from src.modules.channels.application.publication_import.command.cancel_publication_import.command import (
    CancelPublicationImportCommand,
)
from src.modules.channels.presentation.publication_import.depends import (
    CancelPublicationImportHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogCreateContextDep
from src.modules.channels.presentation.publication_import.http.request.cancel_publication_import import (
    CancelPublicationImportRequest,
)
from src.modules.channels.presentation.publication_import.http.response.cancel_publication_import import (
    CancelPublicationImportResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def cancel_publication_import(
    preparation_id: UUID,
    payload: CancelPublicationImportRequest,
    context: CatalogCreateContextDep,
    handler: CancelPublicationImportHandlerDep,
) -> CancelPublicationImportResponse:
    """Преобразует запрос и доверенный контекст в конкретную команду."""
    try:
        result = await handler.execute(
            CancelPublicationImportCommand(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                preparation_id,
                payload.expected_revision,
            )
        )
        return CancelPublicationImportResponse(
            preparation_id=result.preparation_id, revision=result.revision
        )
    except ChannelsError as error:
        raise http_error(error) from error
