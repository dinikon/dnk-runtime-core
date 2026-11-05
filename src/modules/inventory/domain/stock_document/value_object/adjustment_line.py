from dataclasses import dataclass

from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockAdjustmentLineError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


@dataclass(frozen=True, slots=True)
class StockAdjustmentLineVO:
    """Фиксирует физические измерения и переход от исторического остатка к посчитанному."""

    dimensions: StockDimensionsVO
    position_id: StockPositionIdVO | None
    position_version: int | None
    expected_qty: QuantityVO
    target_qty: QuantityVO

    def __post_init__(self) -> None:
        """Требует ненулевую разницу, парные ссылки позиции и единичные серийные остатки."""
        if (
            not isinstance(self.dimensions, StockDimensionsVO)
            or not isinstance(self.expected_qty, QuantityVO)
            or not isinstance(self.target_qty, QuantityVO)
            or self.expected_qty == self.target_qty
            or (self.position_id is None) != (self.position_version is None)
            or (
                self.position_id is not None
                and not isinstance(self.position_id, StockPositionIdVO)
            )
            or (
                self.position_version is not None
                and (
                    type(self.position_version) is not int or self.position_version < 0
                )
            )
            or (self.position_id is None and not self.expected_qty.value.is_zero())
        ):
            raise InvalidStockAdjustmentLineError(
                "Нужна ненулевая корректировка с парными ID/версией позиции; найденный запас начинается с нуля."
            )
        if self.dimensions.serial_id is not None and (
            self.expected_qty.value not in (0, 1) or self.target_qty.value not in (0, 1)
        ):
            raise InvalidStockAdjustmentLineError(
                "Остаток SERIAL может быть только ноль или одна штука."
            )

    @property
    def quantity_delta(self) -> StockDeltaVO:
        """Вычисляет точную знаковую разницу без зависимости от глобальной точности Decimal."""
        if self.target_qty.value > self.expected_qty.value:
            return StockDeltaVO(
                QuantityArithmeticPolicy.subtract(
                    self.target_qty, self.expected_qty
                ).value
            )
        return StockDeltaVO(
            QuantityArithmeticPolicy.subtract(
                self.expected_qty, self.target_qty
            ).value.copy_negate()
        )
