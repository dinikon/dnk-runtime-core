from src.modules.inventory.domain.policy.stock_position_transition_serial_presence import (
    StockPositionTransitionSerialPresencePolicy,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionTransitionSerialPresenceError,
)
from src.modules.inventory.domain.stock_document.internal_move_error import (
    InternalMoveSerialPresenceError,
)
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)


class InternalMoveSerialPresencePolicy:
    """Переносит существующее единственное присутствие SERIAL без создания нового экземпляра."""

    @staticmethod
    def ensure_movable(
        *,
        lines: tuple[StockExecutionLine, ...],
        positions: tuple[StockPosition, ...],
        presence: tuple[StockSerialPresenceSnapshot, ...],
    ) -> None:
        """Требует единственный положительный источник каждого перемещаемого экземпляра."""
        try:
            StockPositionTransitionSerialPresencePolicy.ensure_movable(
                lines=lines, positions=positions, presence=presence
            )
        except StockPositionTransitionSerialPresenceError as exc:
            raise InternalMoveSerialPresenceError(str(exc)) from exc
