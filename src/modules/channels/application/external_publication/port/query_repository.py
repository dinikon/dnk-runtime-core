from typing import Protocol
from uuid import UUID
from src.modules.channels.application.external_publication.query.list_publications.dto import (
    PublicationPageDTO,
)
from src.modules.channels.application.external_publication.query.get_publication.dto import (
    PublicationDetailsDTO,
)


class PublicationQueryRepositoryProtocol(Protocol):
    """Читает поля публикаций напрямую из tenant-проекций."""

    async def list(
        self, channel_id: UUID, offset: int, limit: int
    ) -> PublicationPageDTO:
        """Возвращает только публикации текущей ревизии подключения."""
        ...

    async def get(
        self, channel_id: UUID, publication_id: UUID
    ) -> PublicationDetailsDTO | None:
        """Возвращает карточку и её позиции, ограниченные каналом и подключением."""
        ...
