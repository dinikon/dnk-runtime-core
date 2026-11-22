from src.modules.feed_builder.application.feed.query.list_transforms.query import (
    ListTransformsQuery,
)
from src.modules.feed_builder.presentation.feed.depends import ListTransformsHandlerDep
from src.modules.feed_builder.presentation.feed.http.response.list_transforms import (
    ListTransformsResponse,
    TransformResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def list_transforms(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListTransformsHandlerDep,
) -> ListTransformsResponse:
    """Возвращает метаданные после проверки прав, не выдавая значения товаров."""
    await require_feed_access(context, authorization, action="feed_builder.feed.read")
    result = await handler.execute(ListTransformsQuery())
    return ListTransformsResponse(
        items=tuple(
            TransformResponse(
                operation=item.operation,
                label=item.label,
                field_kinds=item.field_kinds,
                parameter_kind=item.parameter_kind,
            )
            for item in result.items
        )
    )
