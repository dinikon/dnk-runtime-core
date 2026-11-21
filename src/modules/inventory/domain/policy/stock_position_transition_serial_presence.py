from src.modules.inventory.domain.stock_position.error import (
    StockPositionTransitionSerialPresenceError,
)
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)


class StockPositionTransitionSerialPresencePolicy:
    """Переносит существующее единственное присутствие SERIAL без создания нового экземпляра."""

    @staticmethod
    def ensure_movable(
        *,
        lines: tuple[StockExecutionLine, ...],
        positions: tuple[StockPosition, ...],
        presence: tuple[StockSerialPresenceSnapshot, ...],
    ) -> None:
        """Требует единственный положительный источник каждого перемещаемого экземпляра."""
        serial_sources = {
            line.route.dimensions[0].serial_id: line.route.dimensions[0]
            for line in lines
            if line.route.dimensions[0].serial_id is not None
        }
        by_serial = {snapshot.serial_id: snapshot for snapshot in presence}
        if len(by_serial) != len(presence) or set(by_serial) != set(serial_sources):
            raise StockPositionTransitionSerialPresenceError(
                "Нужен полный снимок присутствия перемещаемых экземпляров."
            )
        by_dimensions = {position.dimensions: position for position in positions}
        for identifier, dimensions in serial_sources.items():
            snapshot = by_serial[identifier]
            snapshot.ensure_valid()
            source = by_dimensions.get(dimensions)
            if (
                source is None
                or len(snapshot.positions) != 1
                or snapshot.positions[0] != source.counting_snapshot()
            ):
                raise StockPositionTransitionSerialPresenceError(
                    "Экземпляр должен присутствовать только в выбранном источнике."
                )
