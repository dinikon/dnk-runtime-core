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
    VariantSelectionHandlerDep,
)
from src.modules.feed_builder.presentation.publication.http.response.variant_selection import (
    VariantSelectionResponse,
    VariantSelectionItemResponse,
)
from src.modules.feed_builder.application.publication.query.variant_selection.query import (
    VariantSelectionQuery,
)


async def variant_selection(
    feed_id: UUID,
    catalog_item_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: VariantSelectionHandlerDep,
    locale: str = Query(default="uk", min_length=2, max_length=64),
) -> VariantSelectionResponse:
    """Возвращает полный ограниченный снимок для явного выбора всех текущих вариантов."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.read", feed_id=feed_id
    )
    await require_feed_access(
        context, authorization, action="feed_builder.publication.add", feed_id=feed_id
    )
    await require_catalog_subjects(context, authorization, (catalog_item_id,))
    try:
        result = await handler.execute(
            VariantSelectionQuery(feed_id, catalog_item_id, locale)
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
            s.reference.catalog_variant_id.uuid
            for s in result.items
            if s.reference.catalog_variant_id
        ),
    )
    return VariantSelectionResponse(
        items=tuple(
            VariantSelectionItemResponse(
                catalog_item_id=s.reference.catalog_item_id.uuid,
                catalog_variant_id=s.reference.catalog_variant_id.uuid,
                title=s.title,
                sku=s.sku,
            )
            for s in result.items
            if s.reference.catalog_variant_id
        )
    )
