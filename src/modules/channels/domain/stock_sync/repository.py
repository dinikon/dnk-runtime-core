from typing import Protocol

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.stock_sync.aggregate import StockSync


class StockSyncRepositoryProtocol(Protocol):
    """Хранилище агрегатов на общей tenant-транзакции."""

    async def get(self, publication_id: EntityIdVO) -> StockSync | None:
        """Загружает текущий цикл остатка площадки."""
        ...

    async def save(self, state: StockSync) -> None:
        """Сохраняет проверенное состояние без commit."""
        ...

    async def for_operation(self, operation_id: EntityIdVO) -> tuple[StockSync, ...]:
        """Загружает участников одного семейного задания."""
        ...
