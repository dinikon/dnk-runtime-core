from dataclasses import dataclass

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)


@dataclass(frozen=True, slots=True)
class StockSerialPresenceSnapshot:
    """Передаёт полное положительное присутствие экземпляра в tenant, включая чужие склады и владельцев."""

    serial_id: StockSerialIdVO
    positions: tuple[StockPositionCountingSnapshot, ...]

    def ensure_valid(self) -> None:
        """Требует явный снимок отсутствия либо единственную положительную позицию того же SERIAL."""
        if (
            not isinstance(self.serial_id, StockSerialIdVO)
            or not isinstance(self.positions, tuple)
            or len(self.positions) > 1
        ):
            raise StockAdjustmentError(
                "Присутствие экземпляра — пустой tuple либо одна положительная позиция."
            )
        for position in self.positions:
            if not isinstance(position, StockPositionCountingSnapshot):
                raise StockAdjustmentError(
                    "Нужен снимок количества и версии серийной позиции."
                )
            position.ensure_valid()
            if (
                position.dimensions.serial_id != self.serial_id
                or position.on_hand_qty.value != 1
            ):
                raise StockAdjustmentError(
                    "Положительное присутствие требует того же SERIAL и 1 PCS."
                )
