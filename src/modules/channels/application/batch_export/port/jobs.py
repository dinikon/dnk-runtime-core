from datetime import datetime
from typing import Protocol
from uuid import UUID


class BatchExportJobs(Protocol):
    """Планирует шаг и расписание в транзакции их владельца."""

    async def batch_export(
        self, tenant_id: UUID, run_id: UUID, sequence: int, at: datetime
    ) -> None:
        """Планирует уникальный шаг без payload и секретов."""
        ...

    async def daily_export(
        self, tenant_id: UUID, channel_id: UUID, revision: int, at: datetime
    ) -> None:
        """Планирует единственное исполнение локального календарного дня."""
        ...

    async def is_recoverable(self, tenant_id: UUID, job_id: UUID) -> bool:
        """Проверяет наличие действующего durable шага для безопасного восстановления."""
        ...
