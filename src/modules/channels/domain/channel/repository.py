"""Порт хранения агрегата в уже открытом tenant UoW."""

from typing import Protocol

from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ChannelRepositoryProtocol(Protocol):
    """Хранение агрегатов и сериализация притязаний на магазин."""

    async def get(
        self, channel_id: EntityIdVO, *, for_update: bool = False
    ) -> Channel | None:
        """Восстанавливает канал текущего tenant."""
        ...

    async def save(self, channel: Channel) -> None:
        """Сохраняет полный агрегат без commit."""
        ...

    async def delete(self, channel_id: EntityIdVO) -> None:
        """Удаляет агрегат с его подключением."""
        ...

    async def identity_available(
        self, channel_id: EntityIdVO, identity: ResourceIdentityVO
    ) -> bool:
        """Блокирует ключ ресурса до конца UoW и проверяет владельца."""
        ...
