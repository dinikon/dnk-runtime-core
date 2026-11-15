from src.modules.inventory.presentation.stock_document.status_change_depends import (
    GetStatusTransitionsHandlerDep,
)
from src.modules.inventory.application.stock_document.query.get_status_transitions.query import (
    GetStatusTransitionsQuery,
)
from src.modules.inventory.presentation.stock_document.http.response.get_status_transitions import (
    GetStatusTransitionsResponse,
)


async def get_status_transitions(
    handler: GetStatusTransitionsHandlerDep,
) -> GetStatusTransitionsResponse:
    """Отдаёт матрицу из Application без собственной валидации переходов."""
    return GetStatusTransitionsResponse.from_dto(
        await handler.execute(GetStatusTransitionsQuery())
    )
