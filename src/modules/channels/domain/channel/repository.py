from typing import Protocol

from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO


class ChannelRepositoryProtocol(Protocol):
    """Хранит агрегаты в tenant-контексте внешнего UoW без управления транзакцией."""

    async def add(self, channel: Channel) -> None:
        """Добавляет новый агрегат в текущую транзакцию."""
        ...

    async def get_for_update(self, channel_id: ChannelIdVO) -> Channel | None:
        """Загружает и блокирует агрегат до завершения UoW; при отсутствии даёт None."""
        ...

    async def save(self, channel: Channel) -> None:
        """Сохраняет изменяемое состояние загруженного агрегата без commit."""
        ...

    async def delete(self, channel_id: ChannelIdVO) -> bool:
        """Удаляет агрегат и credentials; сообщает, существовал ли канал."""
        ...
