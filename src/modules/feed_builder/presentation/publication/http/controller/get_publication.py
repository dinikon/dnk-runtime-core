from uuid import UUID
from fastapi import HTTPException, Query
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
    GetPublicationHandlerDep,
    PublicationQueriesDep,
)
from src.modules.feed_builder.presentation.publication.http.response.get_publication import (
    GetPublicationResponse,
)
from src.modules.feed_builder.presentation.publication.http.response.list_publications import (
    PublicationListItemResponse,
)
from src.modules.feed_builder.application.publication.query.get_publication.query import (
    GetPublicationQuery,
)


async def get_publication(
    publication_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    queries: PublicationQueriesDep,
    handler: GetPublicationHandlerDep,
    locale: str = Query(default="uk", min_length=2, max_length=64),
) -> GetPublicationResponse:
    """Читает карточку после проверки доступа к Feed и конкретной позиции."""
    record = await require_publication_access(
        publication_id, queries, context, authorization, "feed_builder.publication.read"
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
        result = await handler.execute(GetPublicationQuery(publication_id, locale))
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
    return GetPublicationResponse(
        publication=PublicationListItemResponse.from_dto(result.publication),
        feed_version=result.feed_version,
        feed_status=result.feed_status,
    )
