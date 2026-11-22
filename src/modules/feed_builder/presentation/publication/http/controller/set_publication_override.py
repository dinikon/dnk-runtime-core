from uuid import UUID

from src.modules.feed_builder.application.publication.command.set_publication_override.command import (
    SetPublicationOverrideCommand,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.presentation.publication.access import (
    require_publication_access,
)
from src.modules.feed_builder.presentation.publication.depends import (
    PublicationQueriesDep,
)
from src.modules.feed_builder.presentation.publication.override_depends import (
    SetPublicationOverrideHandlerDep,
)
from src.modules.feed_builder.presentation.publication.http.override_errors import (
    override_http_error,
)
from src.modules.feed_builder.presentation.publication.http.request.set_publication_override import (
    SetPublicationOverrideRequest,
)
from src.modules.feed_builder.presentation.publication.http.response.set_publication_override import (
    SetPublicationOverrideResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def set_publication_override(
    publication_id: UUID,
    field_id: UUID,
    payload: SetPublicationOverrideRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    queries: PublicationQueriesDep,
    handler: SetPublicationOverrideHandlerDep,
) -> SetPublicationOverrideResponse:
    """Проверяет право изменения публикации и передаёт команду одному полю."""
    record = await require_publication_access(
        publication_id,
        queries,
        context,
        authorization,
        "feed_builder.publication.update",
    )
    try:
        result = await handler.execute(
            SetPublicationOverrideCommand(
                record.feed_id,
                publication_id,
                field_id,
                payload.expected_feed_version,
                payload.expected_version,
                payload.value,
            )
        )
    except FeedBuilderDomainError as exc:
        raise override_http_error(exc, field_id) from exc
    return SetPublicationOverrideResponse(
        publication_version=result.publication_version
    )
