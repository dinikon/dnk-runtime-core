from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.feed_builder.presentation.publication.access import (
    require_catalog_subjects,
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
    RestorePublicationHandlerDep,
    PublicationQueriesDep,
)
from src.modules.feed_builder.application.publication.command.restore_publication.command import (
    RestorePublicationCommand,
)
from src.modules.feed_builder.presentation.publication.http.request.restore_publication import (
    RestorePublicationRequest,
)
from src.modules.feed_builder.presentation.publication.http.response.restore_publication import (
    RestorePublicationResponse,
)


async def restore_publication(
    publication_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RestorePublicationHandlerDep,
    queries: PublicationQueriesDep,
    payload: RestorePublicationRequest,
) -> RestorePublicationResponse:
    """Проверяет права и переводит конкретное намерение в команду агрегата."""
    record = await require_publication_access(
        publication_id,
        queries,
        context,
        authorization,
        "feed_builder.publication.restore",
    )
    await require_catalog_subjects(
        context,
        authorization,
        tuple(
            i
            for i in (record.catalog_item_id, record.catalog_variant_id)
            if i is not None
        ),
    )
    try:
        result = await handler.execute(
            RestorePublicationCommand(
                record.feed_id, publication_id, payload.expected_version
            )
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
    return RestorePublicationResponse(
        id=result.id,
        status=result.status,
        version=result.version,
        updated_at=result.updated_at,
    )
