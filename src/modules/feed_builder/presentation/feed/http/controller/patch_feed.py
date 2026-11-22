from uuid import UUID
from fastapi import HTTPException
from src.modules.feed_builder.application.feed.command.update_feed.command import (
    UpdateFeedCommand,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedCodeConflictError,
    FeedVersionConflictError,
    FeedArchivedError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.presentation.feed.depends import UpdateFeedHandlerDep
from src.modules.feed_builder.presentation.feed.http.request.patch_feed import (
    PatchFeedRequest,
)
from src.modules.feed_builder.presentation.feed.http.response.patch_feed import (
    PatchFeedResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def patch_feed(
    feed_id: UUID,
    payload: PatchFeedRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: UpdateFeedHandlerDep,
) -> PatchFeedResponse:
    """Передаёт частичное изменение, не объединяя вложенные настройки форматов."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.update", feed_id=feed_id
    )
    try:
        result = await handler.execute(
            UpdateFeedCommand(
                feed_id=FeedIdVO.from_value(feed_id),
                expected_version=payload.expected_version,
                name=payload.name,
                code=payload.code,
                export_settings=(
                    payload.export_settings.to_dto()
                    if payload.export_settings is not None
                    else None
                ),
            )
        )
    except FeedNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (FeedCodeConflictError, FeedVersionConflictError, FeedArchivedError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except InvalidFeedValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchFeedResponse.from_dto(result)
