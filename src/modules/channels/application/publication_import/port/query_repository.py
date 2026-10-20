from typing import Protocol
from uuid import UUID
from src.modules.channels.application.publication_import.query.get_publication_import.dto import (
    GetPublicationImportResultDTO,
)


class PublicationImportQueryRepositoryProtocol(Protocol):
    """Читает проекцию подготовки без восстановления write-модели."""

    async def get(self, identifier: UUID) -> GetPublicationImportResultDTO:
        """Возвращает проекцию либо ошибку отсутствия."""
        ...
