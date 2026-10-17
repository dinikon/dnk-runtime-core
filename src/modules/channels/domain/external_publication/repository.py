from typing import Protocol
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)


class PublicationRepositoryProtocol(Protocol):
    """Хранит наблюдаемые публикации в общей tenant-транзакции."""

    async def find(
        self,
        channel_id: ChannelIdVO,
        connection_revision: int,
        resource_type: str,
        external_id: str,
    ) -> ExternalPublication | None:
        """Загружает снимок по устойчивой внешней идентичности."""
        ...

    async def save(self, publication: ExternalPublication) -> None:
        """Записывает новую или обновлённую публикацию без commit."""
        ...
