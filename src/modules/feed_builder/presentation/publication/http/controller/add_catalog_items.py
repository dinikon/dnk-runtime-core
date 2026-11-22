from uuid import UUID
from fastapi import HTTPException
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
    AddCatalogItemsHandlerDep,
)
from src.modules.feed_builder.presentation.publication.http.request.add_catalog_items import (
    AddCatalogItemsRequest,
)
from src.modules.feed_builder.presentation.publication.http.response.add_catalog_items import (
    AddCatalogItemsResponse,
    AddedPublicationResponse,
)
from src.modules.feed_builder.application.publication.command.add_catalog_items.command import (
    AddCatalogItemsCommand,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def add_catalog_items(
    feed_id: UUID,
    payload: AddCatalogItemsRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: AddCatalogItemsHandlerDep,
) -> AddCatalogItemsResponse:
    """Проверяет доступ ко всему пакету до выполнения атомарной команды."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.read", feed_id=feed_id
    )
    await require_feed_access(
        context, authorization, action="feed_builder.publication.add", feed_id=feed_id
    )
    await require_catalog_subjects(
        context,
        authorization,
        tuple(
            i
            for r in payload.item_references
            for i in (r.catalog_item_id, r.catalog_variant_id)
            if i is not None
        ),
    )
    try:
        result = await handler.execute(
            AddCatalogItemsCommand(
                FeedIdVO(feed_id),
                payload.expected_feed_version,
                tuple(
                    CatalogProductReferenceVO(
                        EntityIdVO(r.catalog_item_id),
                        (
                            EntityIdVO(r.catalog_variant_id)
                            if r.catalog_variant_id
                            else None
                        ),
                    )
                    for r in payload.item_references
                ),
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
    return AddCatalogItemsResponse(
        feed_id=result.feed_id,
        feed_version=result.feed_version,
        items=tuple(
            AddedPublicationResponse(
                id=i.id,
                catalog_item_id=i.catalog_item_id,
                catalog_variant_id=i.catalog_variant_id,
                status=i.status,
                version=i.version,
                outcome=i.outcome,
            )
            for i in result.items
        ),
    )
