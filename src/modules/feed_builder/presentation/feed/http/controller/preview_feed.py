from uuid import UUID

from fastapi import HTTPException

from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationDependencyUnavailableError,
)
from src.modules.feed_builder.application.feed.query.preview_feed.query import (
    PreviewFeedQuery,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedNotFoundError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.feed_builder.presentation.feed.export_depends import (
    PreviewFeedHandlerDep,
)
from src.modules.feed_builder.presentation.feed.http.request.preview_feed import (
    PreviewFeedRequest,
)
from src.modules.feed_builder.presentation.feed.http.response.preview_feed import (
    PreviewColumnResponse,
    PreviewFeedResponse,
    PreviewRowResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def preview_feed(
    feed_id: UUID,
    payload: PreviewFeedRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: PreviewFeedHandlerDep,
) -> PreviewFeedResponse:
    """Возвращает рассчитанные поля сохранённой схемы для образца публикаций."""
    for action in (
        "feed_builder.feed.read",
        "feed_builder.publication.read",
        "feed_builder.feed.calculation_preview",
    ):
        await require_feed_access(
            context, authorization, action=action, feed_id=feed_id
        )
    try:
        result = await handler.execute(
            PreviewFeedQuery(FeedIdVO(feed_id), payload.expected_version)
        )
    except FeedNotFoundError as exc:
        raise HTTPException(
            404, {"code": "FEED_NOT_FOUND", "message": str(exc)}
        ) from exc
    except (FeedArchivedError, FeedVersionConflictError) as exc:
        raise HTTPException(
            409, {"code": "FEED_CONFLICT", "message": str(exc)}
        ) from exc
    except CalculationDependencyUnavailableError as exc:
        raise HTTPException(
            503, {"code": "DEPENDENCY_UNAVAILABLE", "message": str(exc)}
        ) from exc
    return PreviewFeedResponse(
        feed_id=result.feed_id,
        version=result.version,
        as_of=result.as_of,
        total_enabled=result.total_enabled,
        columns=tuple(
            PreviewColumnResponse.model_validate(column) for column in result.columns
        ),
        rows=tuple(PreviewRowResponse.model_validate(row) for row in result.rows),
    )
