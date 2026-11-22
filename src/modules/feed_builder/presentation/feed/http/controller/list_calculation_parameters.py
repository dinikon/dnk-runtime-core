from src.modules.feed_builder.application.feed.query.list_calculation_parameters.query import (
    ListCalculationParametersQuery,
)
from src.modules.feed_builder.presentation.feed.depends import (
    ListCalculationParametersHandlerDep,
)
from src.modules.feed_builder.presentation.feed.http.response.list_calculation_parameters import (
    ListCalculationParametersResponse,
    CalculationParameterResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def list_calculation_parameters(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListCalculationParametersHandlerDep,
) -> ListCalculationParametersResponse:
    """Возвращает реализованный реестр после проверки доступа к FeedBuilder."""
    await require_feed_access(context, authorization, action="feed_builder.feed.read")
    result = await handler.execute(ListCalculationParametersQuery())
    return ListCalculationParametersResponse(
        items=tuple(
            CalculationParameterResponse(
                id=item.id,
                label=item.label,
                value_type=item.value_type,
                nullable=item.nullable,
            )
            for item in result.items
        )
    )
