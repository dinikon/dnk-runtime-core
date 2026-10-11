from datetime import datetime
from typing import Protocol
from uuid import UUID


class FilePurgeQueueProtocol(Protocol):
    """Порт durable заданий purge в общей транзакции, без брокера и ORM."""

    async def schedule(
        self, tenant_id: UUID, file_id: UUID, job_id: UUID, run_at: datetime
    ) -> None:
        """Записывает отдельную job удаления; commit остаётся за внешним UoW."""
        ...

    async def terminal_or_missing(
        self, tenant_id: UUID, job_ids: tuple[UUID, ...]
    ) -> frozenset[UUID]:
        """Возвращает terminal/missing IDs для ограниченной tenant-порции recovery."""
        ...
