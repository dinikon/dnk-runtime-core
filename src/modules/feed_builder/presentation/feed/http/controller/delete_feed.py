from uuid import UUID
from typing import Annotated
from fastapi import HTTPException, Query, Response
from src.modules.feed_builder.application.feed.command.archive_feed.command import (
    ArchiveFeedCommand,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedVersionConflictError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.presentation.feed.depends import ArchiveFeedHandlerDep
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def delete_feed(
    feed_id: UUID,
    expected_version: Annotated[int, Query(ge=1, le=9223372036854775807)],
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ArchiveFeedHandlerDep,
) -> Response:
    """Архивирует Feed и возвращает 204 без тела; строка и её код сохраняются."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.archive", feed_id=feed_id
    )
    try:
        await handler.execute(
            ArchiveFeedCommand(
                feed_id=FeedIdVO.from_value(feed_id),
                expected_version=expected_version,
            )
        )
    except FeedNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FeedVersionConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InvalidFeedValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(status_code=204)
