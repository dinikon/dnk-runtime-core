from typing import Protocol
from uuid import UUID
from datetime import datetime
from src.modules.files.application.port.query_repository import FileContentLocationDTO


class ArtifactFilesFacadeProtocol(Protocol):
    """Публичный двухфазный контракт файлов: сеть выполняется вне SQL-транзакции."""

    async def reserve(
        self,
        tenant_id: UUID,
        file_id: UUID,
        name: str,
        content_type: str,
        size: int,
        now: datetime,
    ) -> FileContentLocationDTO:
        """Регистрирует идемпотентную загрузку и возвращает приватные координаты."""
        ...

    async def confirm(self, file_id: UUID, size: int) -> None:
        """Подтверждает фактическую запись по уже зарегистрированной загрузке."""
        ...

    async def location(self, tenant_id: UUID, file_id: UUID) -> FileContentLocationDTO:
        """Возвращает координаты только готового файла без открытия сети."""
        ...
