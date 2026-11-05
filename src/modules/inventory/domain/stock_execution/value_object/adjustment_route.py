from dataclasses import dataclass

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.stock_document.value_object.adjustment_line import (
    StockAdjustmentLineVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)


@dataclass(frozen=True, slots=True)
class StockAdjustmentExecutionRouteVO:
    """Связывает исходную поправку с реальной позицией, не подменяя отсутствие позиции в FOUND."""

    adjustment: StockAdjustmentLineVO
    position_id: StockPositionIdVO
    expected_position_version: int

    def __post_init__(self) -> None:
        """Требует прежнюю позицию/версию либо новую позицию версии ноль для найденного запаса."""
        if (
            not isinstance(self.adjustment, StockAdjustmentLineVO)
            or not isinstance(self.position_id, StockPositionIdVO)
            or type(self.expected_position_version) is not int
            or self.expected_position_version < 0
        ):
            raise StockAdjustmentError(
                "Нужны поправка, позиция и строгая неотрицательная версия."
            )
        if self.adjustment.position_id is None:
            if self.expected_position_version != 0:
                raise StockAdjustmentError(
                    "FOUND применяется к новой нулевой позиции версии 0."
                )
        elif (self.position_id, self.expected_position_version) != (
            self.adjustment.position_id,
            self.adjustment.position_version,
        ):
            raise StockAdjustmentError(
                "Существующая позиция и её версия должны совпадать с основанием."
            )

    @property
    def dimensions(self) -> tuple[StockDimensionsVO, ...]:
        """Передаёт единственные физические измерения поправки."""
        return (self.adjustment.dimensions,)
