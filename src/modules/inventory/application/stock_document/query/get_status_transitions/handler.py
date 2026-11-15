from src.modules.inventory.domain.policy.stock_status_transition import (
    StockStatusTransitionPolicy,
)
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.application.stock_document.query.get_status_transitions.query import (
    GetStatusTransitionsQuery,
)
from src.modules.inventory.application.stock_document.query.get_status_transitions.dto import (
    GetStatusTransitionsResultDTO,
    StatusTransitionDTO,
)


class GetStatusTransitionsHandler:
    """Проецирует публичные правила Domain без SQL и изменений."""

    async def execute(
        self, query: GetStatusTransitionsQuery
    ) -> GetStatusTransitionsResultDTO:
        """Возвращает каждое исходное состояние и его разрешённые цели."""
        return GetStatusTransitionsResultDTO(
            tuple(
                StatusTransitionDTO(
                    source.value,
                    tuple(
                        value.value
                        for value in StockStatusTransitionPolicy.allowed_targets(source)
                    ),
                )
                for source in StockStatus
            )
        )
