from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.sales_error import SalesError, SalesConflictError


@dataclass(frozen=True, slots=True)
class FunnelPositionVO:
    """Единственная текущая позиция карточки в процессе."""

    funnel_id: EntityIdVO
    stage_id: EntityIdVO
    revision: int = 1

    def __post_init__(self) -> None:
        """Проверяет идентификаторы и положительную версию."""
        object.__setattr__(self, "funnel_id", EntityIdVO.from_value(self.funnel_id))
        object.__setattr__(self, "stage_id", EntityIdVO.from_value(self.stage_id))
        if self.revision < 1:
            raise SalesError("Некорректная позиция воронки.")

    def move(
        self, funnel_id: EntityIdVO, stage_id: EntityIdVO, expected_revision: int
    ) -> "FunnelPositionVO":
        """Создаёт новую позицию после проверки версии; повтор является no-op."""
        if expected_revision != self.revision:
            raise SalesConflictError("Карточка уже перемещена. Обновите положение.")
        funnel_id = EntityIdVO.from_value(funnel_id)
        stage_id = EntityIdVO.from_value(stage_id)
        if (funnel_id, stage_id) == (self.funnel_id, self.stage_id):
            return self
        return FunnelPositionVO(funnel_id, stage_id, self.revision + 1)
