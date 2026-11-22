from typing import cast
from uuid import UUID
from fastapi import HTTPException
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.command import (
    SaveFeedSchemaDraftCommand,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.application.feed.schema_error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedVersionConflictError,
    FeedArchivedError,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.domain.feed.calculation.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.presentation.feed.depends import (
    SaveFeedSchemaDraftHandlerDep,
)
from src.modules.feed_builder.presentation.feed.http.request.put_feed_schema import (
    PutFeedSchemaRequest,
)
from src.modules.feed_builder.presentation.feed.http.response.put_feed_schema import (
    PutFeedSchemaResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def put_feed_schema(
    feed_id: UUID,
    payload: PutFeedSchemaRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: SaveFeedSchemaDraftHandlerDep,
) -> PutFeedSchemaResponse:
    """Сохраняет весь снимок, явно переводя ожидаемые ошибки в адресованные ответы."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.update", feed_id=feed_id
    )
    try:
        result = await handler.execute(
            SaveFeedSchemaDraftCommand(
                FeedIdVO.from_value(feed_id),
                payload.expected_version,
                cast(
                    JsonObject,
                    payload.definition.model_dump(mode="json", exclude_unset=True),
                ),
            )
        )
    except FeedNotFoundError as exc:
        raise HTTPException(
            404, {"code": "FEED_NOT_FOUND", "message": str(exc)}
        ) from exc
    except FeedVersionConflictError as exc:
        raise HTTPException(
            409, {"code": "VERSION_CONFLICT", "message": str(exc)}
        ) from exc
    except FeedArchivedError as exc:
        raise HTTPException(
            409, {"code": "FEED_ARCHIVED", "message": str(exc)}
        ) from exc
    except (FeedBuilderDomainError, InvalidFeedSchemaDocumentError) as exc:
        path = list(exc.path)
        if path[:2] == ["schema", "fields"]:
            path = ["definition", "root", "fields", *path[2:]]
        identifier = None
        if (
            len(path) > 3
            and path[:3] == ["definition", "root", "fields"]
            and isinstance(path[3], int)
            and path[3] < len(payload.definition.root.fields)
        ):
            identifier = payload.definition.root.fields[path[3]].id
        raise HTTPException(
            422,
            {
                "code": (
                    exc.code
                    if isinstance(exc, CalculationDefinitionError)
                    else "SCHEMA_INVALID"
                ),
                "message": str(exc),
                "field_id": identifier,
                "path": path,
            },
        ) from exc
    return PutFeedSchemaResponse.from_dto(result)
