from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.feed_builder.presentation.publication.access import (
    require_catalog_subjects,
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
    ListPublicationsHandlerDep,
)
from src.modules.feed_builder.presentation.publication.http.response.list_publications import (
    ListPublicationsResponse,
)
from src.modules.feed_builder.application.publication.query.list_publications.query import (
    ListPublicationsQuery,
)


async def list_publications(
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListPublicationsHandlerDep,
    locale: str = Query(default="uk", min_length=2, max_length=64),
    search: str | None = Query(default=None, max_length=255),
    status: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListPublicationsResponse:
    """Возвращает ограниченную страницу с проверкой прав на подписи Catalog."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.read", feed_id=feed_id
    )
    await require_feed_access(
        context, authorization, action="feed_builder.publication.read", feed_id=feed_id
    )
    principal = context.principal
    assert principal is not None and principal.tenant_id is not None
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="catalog.item.read",
        resource_type="catalog.item",
        resource_id=None,
    ):
        raise HTTPException(
            403,
            {
                "code": "SOURCE_ACCESS_DENIED",
                "message": "Недостаточно прав для чтения списка Catalog.",
            },
        )
    try:
        result = await handler.execute(
            ListPublicationsQuery(feed_id, locale, search, status, limit, offset)
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
    await require_catalog_subjects(
        context,
        authorization,
        tuple(
            i
            for item in result.items
            for i in (item.record.catalog_item_id, item.record.catalog_variant_id)
            if i is not None
        ),
    )
    return ListPublicationsResponse.from_dto(result)
