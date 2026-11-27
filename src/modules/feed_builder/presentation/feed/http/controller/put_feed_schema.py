from uuid import UUID
from fastapi import HTTPException
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.command import (
    SaveFeedSchemaDraftCommand,
)
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.expression.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.presentation.feed.http.schema.graph import (
    FieldGraphSchema,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedVersionConflictError,
    FeedArchivedError,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.application.feed.graph.registry import node_codec
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
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
    """Сохраняет версионированный граф через существующий API."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.update", feed_id=feed_id
    )
    try:
        result = await handler.execute(
            SaveFeedSchemaDraftCommand(
                FeedIdVO.from_value(feed_id),
                payload.expected_version,
                payload.definition.to_input(),
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
        path = exc.path
        if path[:1] == ("schema",):
            path = ("definition", *path[1:])
        field_id = _issue_field_id(payload.definition, path) if len(path) >= 3 else None
        raise HTTPException(
            422,
            {
                "code": (
                    exc.code
                    if isinstance(exc, CalculationDefinitionError)
                    else "SCHEMA_INVALID"
                ),
                "message": str(exc),
                "field_id": field_id,
                "path": list(path),
            },
        ) from exc
    return PutFeedSchemaResponse.from_dto(result)


def _issue_field_id(graph: FieldGraphSchema, path: tuple[str | int, ...]) -> str | None:
    """Находит ноду ошибки либо первую ноду, ссылающуюся на дерево."""
    index = path[2]
    if not isinstance(index, int) or index < 0:
        return None
    if path[:2] == ("definition", "fields") and index < len(graph.fields):
        return graph.fields[index].id
    if path[:2] == ("definition", "categoryTrees") and index < len(graph.categoryTrees):
        tree_id = graph.categoryTrees[index].id
        category_type = node_codec(FieldValueType.CATEGORY.value).type_id
        return next(
            (
                field.id
                for field in graph.fields
                if field.typeId == category_type
                and field.data.get("source") == "feed"
                and field.data.get("treeId") == tree_id
            ),
            None,
        )
    return None
