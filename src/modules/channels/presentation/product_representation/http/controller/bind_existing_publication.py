from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.product_representation.command.bind_existing_publication.command import (
    BindExistingPublicationCommand,
)
from src.modules.channels.presentation.product_representation.depends import (
    BindExistingPublicationHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.product_representation.http.request.bind_existing_publication import (
    BindExistingPublicationRequest,
)
from src.modules.channels.presentation.product_representation.http.response.bind_existing_publication import (
    BindExistingPublicationResponse,
)


async def bind_existing_publication(
    publication_id: UUID,
    context: CatalogLinkContextDep,
    handler: BindExistingPublicationHandlerDep,
    payload: BindExistingPublicationRequest,
) -> BindExistingPublicationResponse:
    """Преобразует HTTP bind_existing_publication в конкретный use case доверенного tenant."""
    try:
        request = BindExistingPublicationCommand(
            UUID(context.principal.tenant_id),
            UUID(context.principal.user_id),
            publication_id,
            payload.catalog_item_id,
            payload.expected_revision,
        )
        result = await handler.execute(request)
        return BindExistingPublicationResponse(**asdict(result))
    except ChannelsError as error:
        raise http_error(error) from error
