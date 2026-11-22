from src.modules.feed_builder.application.feed.query.list_calculation_operations.query import (
    ListCalculationOperationsQuery,
)
from src.modules.feed_builder.presentation.feed.depends import (
    ListCalculationOperationsHandlerDep,
)
from src.modules.feed_builder.presentation.feed.http.response.list_calculation_operations import (
    ListCalculationOperationsResponse,
    CalculationOperationResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def list_calculation_operations(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListCalculationOperationsHandlerDep,
) -> ListCalculationOperationsResponse:
    """Возвращает реализованный реестр после проверки доступа к FeedBuilder."""
    await require_feed_access(context, authorization, action="feed_builder.feed.read")
    result = await handler.execute(ListCalculationOperationsQuery())
    return ListCalculationOperationsResponse(
        items=tuple(
            CalculationOperationResponse(
                code=item.code,
                category=item.category,
                label=item.label,
                min_arguments=item.min_arguments,
                max_arguments=item.max_arguments,
            )
            for item in result.items
        ),
        engine_version=result.engine_version,
        precision=result.precision,
        max_depth=result.max_depth,
        max_nodes=result.max_nodes,
        max_rules=result.max_rules,
        max_collection_items=result.max_collection_items,
    )
