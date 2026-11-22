from src.modules.feed_builder.application.feed.query.list_source_paths.query import (
    ListSourcePathsQuery,
)
from src.modules.feed_builder.presentation.feed.depends import ListSourcePathsHandlerDep
from src.modules.feed_builder.presentation.feed.http.response.list_source_paths import (
    ListSourcePathsResponse,
    SourcePathResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def list_source_paths(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListSourcePathsHandlerDep,
) -> ListSourcePathsResponse:
    """Возвращает метаданные после проверки прав, не выдавая значения товаров."""
    await require_feed_access(context, authorization, action="feed_builder.feed.read")
    result = await handler.execute(ListSourcePathsQuery())
    return ListSourcePathsResponse(
        items=tuple(
            SourcePathResponse(
                provider=item.provider,
                path=item.path,
                label=item.label,
                field_kinds=item.field_kinds,
                requires_locale=item.requires_locale,
            )
            for item in result.items
        )
    )
