from uuid import UUID

from fastapi import HTTPException

from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationDependencyUnavailableError,
)
from src.modules.feed_builder.application.publication.query.get_publication_fields.query import (
    GetPublicationFieldsQuery,
)
from src.modules.feed_builder.domain.feed.error import FeedNotFoundError
from src.modules.feed_builder.domain.publication.error import PublicationNotFoundError
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.feed_builder.presentation.publication.access import (
    require_publication_access,
)
from src.modules.feed_builder.presentation.publication.depends import (
    PublicationQueriesDep,
)
from src.modules.feed_builder.presentation.publication.override_depends import (
    GetPublicationFieldsHandlerDep,
)
from src.modules.feed_builder.presentation.publication.http.response.get_publication_fields import (
    GetPublicationFieldsResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_publication_fields(
    publication_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    queries: PublicationQueriesDep,
    handler: GetPublicationFieldsHandlerDep,
) -> GetPublicationFieldsResponse:
    """Возвращает исходные и текущие значения в пределах доступного фида."""
    record = await require_publication_access(
        publication_id, queries, context, authorization, "feed_builder.publication.read"
    )
    await require_feed_access(
        context,
        authorization,
        action="feed_builder.feed.calculation_preview",
        feed_id=record.feed_id,
    )
    try:
        result = await handler.execute(
            GetPublicationFieldsQuery(record.feed_id, publication_id)
        )
    except (FeedNotFoundError, PublicationNotFoundError) as exc:
        raise HTTPException(
            404, {"code": "PUBLICATION_RESOURCE_NOT_FOUND", "message": str(exc)}
        ) from exc
    except CalculationDependencyUnavailableError as exc:
        raise HTTPException(
            503, {"code": "DEPENDENCY_UNAVAILABLE", "message": str(exc)}
        ) from exc
    return GetPublicationFieldsResponse.model_validate(result)
