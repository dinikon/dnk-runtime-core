from typing import Annotated
from uuid import UUID

from fastapi import Query

from src.modules.feed_builder.application.publication.command.reset_publication_override.command import (
    ResetPublicationOverrideCommand,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.presentation.publication.access import (
    require_publication_access,
)
from src.modules.feed_builder.presentation.publication.depends import (
    PublicationQueriesDep,
)
from src.modules.feed_builder.presentation.publication.override_depends import (
    ResetPublicationOverrideHandlerDep,
)
from src.modules.feed_builder.presentation.publication.http.override_errors import (
    override_http_error,
)
from src.modules.feed_builder.presentation.publication.http.request.reset_publication_override import (
    ResetPublicationOverrideRequest,
)
from src.modules.feed_builder.presentation.publication.http.response.reset_publication_override import (
    ResetPublicationOverrideResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def reset_publication_override(
    publication_id: UUID,
    field_id: UUID,
    payload: Annotated[ResetPublicationOverrideRequest, Query()],
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    queries: PublicationQueriesDep,
    handler: ResetPublicationOverrideHandlerDep,
) -> ResetPublicationOverrideResponse:
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
            ResetPublicationOverrideCommand(
                record.feed_id,
                publication_id,
                field_id,
                payload.expected_feed_version,
                payload.expected_version,
            )
        )
    except FeedBuilderDomainError as exc:
        raise override_http_error(exc, field_id) from exc
    return ResetPublicationOverrideResponse(
        publication_version=result.publication_version
    )
