from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.expression.value_object.boolean_calculation import (
    BooleanCalculationVO,
)


@dataclass(frozen=True, slots=True)
class CategoryRuleVO:
    """Выбирает один узел фида при выполнении существующего логического условия."""

    id: UUID
    target_id: UUID
    calculation: BooleanCalculationVO
    label: str
    include_descendants: bool = False

    def __post_init__(self) -> None:
        """Проверяет идентичность, цель и тип результата правила."""
        if (
            not isinstance(self.id, UUID)
            or not isinstance(self.target_id, UUID)
            or not isinstance(self.calculation, BooleanCalculationVO)
            or self.calculation.then_value is not True
            or self.calculation.else_value is not False
            or type(self.include_descendants) is not bool
            or not isinstance(self.label, str)
            or not self.label.strip()
            or len(self.label) > 255
        ):
            raise InvalidFeedValueError("Некорректное правило назначения категории.")
