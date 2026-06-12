from typing import Protocol

from src.modules.broadcast.domain.broadcast.entity import BroadcastEntity
from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.shared import EntityIdVO


class BroadcastCommandRepositoryProtocol(Protocol):
    """Порт командного хранения broadcast definitions."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        broadcast_id: BroadcastIdVO,
    ) -> BroadcastEntity | None:
        """Загружает broadcast tenant по id или возвращает None."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        broadcast: BroadcastEntity,
    ) -> BroadcastEntity:
        """Сохраняет broadcast tenant и возвращает актуальную entity."""
        ...


__all__ = ["BroadcastCommandRepositoryProtocol"]
