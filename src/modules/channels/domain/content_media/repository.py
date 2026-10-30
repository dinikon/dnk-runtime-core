from typing import Protocol

from src.modules.channels.domain.content_media.aggregate import ContentMedia
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentMediaRepositoryProtocol(Protocol):
    """Сохраняет корень media на общей tenant-сессии без управления транзакцией."""

    async def get(self, identifier: EntityIdVO) -> ContentMedia | None:
        """Восстанавливает запись с блокировкой для изменения."""
        ...

    async def find(
        self,
        *,
        connection_id: EntityIdVO,
        file_id: EntityIdVO,
        source_fingerprint: str,
        metadata_fingerprint: str,
    ) -> ContentMedia | None:
        """Ищет вариант под общей блокировкой подключения."""
        ...

    async def save(self, media: ContentMedia) -> None:
        """Записывает только новую ревизию без скрытого upsert."""
        ...
