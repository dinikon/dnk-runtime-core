from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.feed_builder.presentation.publication.access import (
    require_publication_access,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedVersionConflictError,
    FeedArchivedError,
)
from src.modules.feed_builder.domain.publication.error import (
    PublicationNotFoundError,
    PublicationVersionConflictError,
    PublicationTransitionError,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationSourceNotFoundError,
    PublicationSourceUnavailableError,
    PublicationSelectionLimitError,
)
from src.modules.feed_builder.presentation.publication.depends import (
    RemovePublicationHandlerDep,
    PublicationQueriesDep,
)
from src.modules.feed_builder.application.publication.command.remove_publication.command import (
    RemovePublicationCommand,
)


async def remove_publication(
    publication_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RemovePublicationHandlerDep,
    queries: PublicationQueriesDep,
    expected_version: int = Query(ge=1, le=9223372036854775807),
) -> None:
    """Проверяет права и переводит конкретное намерение в команду агрегата."""
    record = await require_publication_access(
        publication_id,
        queries,
        context,
        authorization,
        "feed_builder.publication.archive",
    )
    try:
        await handler.execute(
            RemovePublicationCommand(record.feed_id, publication_id, expected_version)
        )
    except (
        FeedNotFoundError,
        PublicationNotFoundError,
        PublicationSourceNotFoundError,
    ) as exc:
        raise HTTPException(
            404, {"code": "PUBLICATION_RESOURCE_NOT_FOUND", "message": str(exc)}
        ) from exc
    except (
        FeedVersionConflictError,
        PublicationVersionConflictError,
        FeedArchivedError,
        PublicationTransitionError,
    ) as exc:
        raise HTTPException(
            409, {"code": "PUBLICATION_CONFLICT", "message": str(exc)}
        ) from exc
    except (FeedBuilderDomainError, PublicationSelectionLimitError) as exc:
        raise HTTPException(
            422, {"code": "PUBLICATION_INVALID", "message": str(exc)}
        ) from exc
    except PublicationSourceUnavailableError as exc:
        raise HTTPException(
            503, {"code": "DEPENDENCY_UNAVAILABLE", "message": str(exc)}
        ) from exc
