from uuid import UUID
from src.modules.channels.application.product_representation.command.unbind_publication.command import (
    UnbindPublicationCommand,
)
from src.modules.channels.presentation.product_representation.depends import (
    UnbindPublicationHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.product_representation.http.request.unbind_publication import (
    UnbindPublicationRequest,
)


async def unbind_publication(
    publication_id: UUID,
    context: CatalogLinkContextDep,
    handler: UnbindPublicationHandlerDep,
    payload: UnbindPublicationRequest,
) -> None:
    """Преобразует HTTP unbind_publication в конкретный use case доверенного tenant."""
    try:
        request = UnbindPublicationCommand(
            UUID(context.principal.tenant_id),
            UUID(context.principal.user_id),
            publication_id,
            payload.binding_id,
            payload.expected_revision,
        )
        await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
