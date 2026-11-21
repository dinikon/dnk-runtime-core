from typing import Protocol
from uuid import UUID


class FileUsagePort(Protocol):
    """Получает факты использования от владельцев ссылок на общей tenant-сессии."""

    async def used(
        self, tenant_id: UUID, file_ids: tuple[UUID, ...]
    ) -> tuple[UUID, ...]:
        """Возвращает используемые ID без открытия транзакций или блокировок потребителей."""
        ...
