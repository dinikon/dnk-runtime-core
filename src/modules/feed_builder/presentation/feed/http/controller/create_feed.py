from fastapi import HTTPException
from src.modules.feed_builder.application.feed.command.create_feed.command import (
    CreateFeedCommand,
)
from src.modules.feed_builder.presentation.feed.depends import CreateFeedHandlerDep
from src.modules.feed_builder.presentation.feed.http.request.create_feed import (
    CreateFeedRequest,
)
from src.modules.feed_builder.presentation.feed.http.response.create_feed import (
    CreateFeedResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.feed_builder.domain.feed.error import (
    FeedCodeConflictError,
    InvalidFeedValueError,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def create_feed(
    payload: CreateFeedRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: CreateFeedHandlerDep,
) -> CreateFeedResponse:
    """Создаёт пустой DRAFT через Application, не принимая схему или статус."""
    await require_feed_access(context, authorization, action="feed_builder.feed.create")
    try:
        result = await handler.execute(
            CreateFeedCommand(
                name=payload.name,
                code=payload.code,
                export_settings=payload.export_settings.to_dto(),
            )
        )
    except FeedCodeConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InvalidFeedValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateFeedResponse.from_dto(result)
