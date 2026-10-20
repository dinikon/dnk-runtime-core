from datetime import datetime
from typing import Protocol
from uuid import UUID


class ContentUpdateJobs(Protocol):
    """Планирует durable шаги на общей транзакции операции."""

    async def content_update(
        self, tenant_id: UUID, run_id: UUID, sequence: int, now: datetime
    ) -> None:
        """Записывает только ID операции и sequence без секретов и текстов."""
        ...
