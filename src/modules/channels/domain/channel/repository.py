from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.aggregate import Channel


class ChannelRepositoryProtocol(Protocol):
    """Сохраняет Channel вместе с его Connection в текущем tenant UoW."""

    async def get(self, identifier: EntityIdVO, *, for_update: bool = True) -> Channel:
        """Загружает корень, при изменении блокирует его строку."""
        ...

    async def by_connection(self, connection_id: EntityIdVO) -> Channel:
        """Разрешает внутренний ID в заблокированный корень."""
        ...

    async def identity_in_use(
        self, kind: str, identity: str, connection_id: EntityIdVO
    ) -> bool:
        """Проверяет дубликат подтверждённого внешнего ресурса."""
        ...

    async def add(self, channel: Channel) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, channel: Channel) -> None:
        """Сохраняет агрегат без commit."""
        ...
