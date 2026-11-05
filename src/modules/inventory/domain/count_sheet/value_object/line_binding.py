from dataclasses import dataclass

from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountSheetLineBindingError,
)
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)


@dataclass(frozen=True, slots=True)
class CountSheetLineBindingVO:
    """Назначает новую дочернюю строку одной существующей позиции основания."""

    line_id: CountLineIdVO
    position_id: StockPositionIdVO

    def __post_init__(self) -> None:
        """Проверяет собственные типизированные ссылки без загрузки позиции."""
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Повторно проверяет ссылки при использовании назначения в публичной политике."""
        if not isinstance(self.line_id, CountLineIdVO) or not isinstance(
            self.position_id, StockPositionIdVO
        ):
            raise InvalidCountSheetLineBindingError(
                "Нужны ID строки ведомости и физической позиции."
            )
