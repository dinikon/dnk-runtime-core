from uuid import UUID
from src.modules.channels.application.publication_import.command.retry_publication_import.command import (
    RetryPublicationImportCommand,
)
from src.modules.channels.presentation.publication_import.depends import (
    RetryPublicationImportHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogCreateContextDep
from src.modules.channels.presentation.publication_import.http.request.retry_publication_import import (
    RetryPublicationImportRequest,
)
from src.modules.channels.presentation.publication_import.http.response.retry_publication_import import (
    RetryPublicationImportResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def retry_publication_import(
    preparation_id: UUID,
    payload: RetryPublicationImportRequest,
    context: CatalogCreateContextDep,
    handler: RetryPublicationImportHandlerDep,
) -> RetryPublicationImportResponse:
    """Преобразует запрос и доверенный контекст в конкретную команду."""
    try:
        result = await handler.execute(
            RetryPublicationImportCommand(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                preparation_id,
                payload.expected_revision,
            )
        )
        return RetryPublicationImportResponse(
            preparation_id=result.preparation_id, revision=result.revision
        )
    except ChannelsError as error:
        raise http_error(error) from error
