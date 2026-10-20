from typing import Protocol
from uuid import UUID
from datetime import datetime


class PublicationImportJobsPort(Protocol):
    """Планирует ограниченные шаги и очистку подготовки на общем UoW."""

    async def prepare(
        self, tenant_id: UUID, preparation_id: UUID, sequence: int, now: datetime
    ) -> None:
        """Ставит устойчивый к повтору шаг без сетевого I/O."""
        ...

    async def cleanup(
        self, tenant_id: UUID, preparation_id: UUID, at: datetime
    ) -> None:
        """Планирует освобождение временных файлов после срока подготовки."""
        ...

    async def is_recoverable(self, tenant_id: UUID, job_id: UUID) -> bool:
        """Различает живой durable job и завершённую либо потерянную доставку."""
        ...
