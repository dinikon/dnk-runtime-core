from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.error import InventoryError


class ReceiptSerialAlreadyPresentError(InventoryError):
    """Запрещает второе положительное присутствие экземпляра при поступлении."""


class ReceiptSerialPresencePolicy:
    """Проверяет глобальное присутствие SERIAL до поступления, включая другие склады и владельцев."""

    @staticmethod
    def ensure_receivable(
        *,
        lines: tuple[StockExecutionLine, ...],
        presence: tuple[StockSerialPresenceSnapshot, ...],
    ) -> None:
        """Требует явное отсутствие каждого поступающего SERIAL и однократное участие в факте."""
        serial_ids = [
            line.route.dimensions[0].serial_id
            for line in lines
            if line.route.dimensions[0].serial_id is not None
        ]
        by_id = {snapshot.serial_id: snapshot for snapshot in presence}
        if (
            len(by_id) != len(presence)
            or set(by_id) != set(serial_ids)
            or len(serial_ids) != len(set(serial_ids))
        ):
            raise ReceiptSerialAlreadyPresentError(
                "Серийный экземпляр повторён или снимок его присутствия неполон."
            )
        for snapshot in presence:
            snapshot.ensure_valid()
            if snapshot.positions:
                raise ReceiptSerialAlreadyPresentError(
                    "Серийный экземпляр уже имеет положительный остаток в tenant."
                )
