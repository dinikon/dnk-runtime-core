from typing import Protocol
from uuid import UUID
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)


class StockPositionRepositoryProtocol(Protocol):
    """Хранит позиции на общей сессии; создание не меняет количество."""

    async def get_or_add_for_update(self, zero: StockPosition) -> StockPosition:
        """Атомарно получает или создаёт ноль по полным измерениям, затем блокирует позицию."""
        ...

    async def save(self, position: StockPosition, *, expected_version: int) -> None:
        """Сохраняет доменный результат с защитой версии без commit."""
        ...

    async def serial_presence(
        self, identifiers: tuple[UUID, ...]
    ) -> tuple[StockSerialPresenceSnapshot, ...]:
        """Возвращает полное положительное присутствие каждого SERIAL во всём tenant."""
        ...
