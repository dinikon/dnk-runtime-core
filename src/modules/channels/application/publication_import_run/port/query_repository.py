from typing import Protocol
from uuid import UUID
from src.modules.channels.application.publication_import_run.query.get_publication_import_run.dto import (
    PublicationImportRunDetailsDTO,
)


class PublicationImportQueryRepositoryProtocol(Protocol):
    """Читает состояние запусков без восстановления агрегата."""

    async def get(
        self, tenant_id: UUID, channel_id: UUID, run_id: UUID | None
    ) -> PublicationImportRunDetailsDTO | None:
        """Возвращает указанный или последний запуск текущего подключения."""
        ...
