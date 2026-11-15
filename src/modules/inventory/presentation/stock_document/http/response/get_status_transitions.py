from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.get_status_transitions.dto import (
    GetStatusTransitionsResultDTO,
)


class StatusTransitionResponse(BaseModel):
    """Сериализует разрешённые цели одного состояния."""

    source_status: str
    target_statuses: tuple[str, ...]


class GetStatusTransitionsResponse(BaseModel):
    """Возвращает конкретный контракт матрицы переходов."""

    items: tuple[StatusTransitionResponse, ...]

    @classmethod
    def from_dto(
        cls, dto: GetStatusTransitionsResultDTO
    ) -> "GetStatusTransitionsResponse":
        """Явно преобразует DTO собственного сценария."""
        return cls(
            items=tuple(
                StatusTransitionResponse(
                    source_status=v.source_status, target_statuses=v.target_statuses
                )
                for v in dto.items
            )
        )
