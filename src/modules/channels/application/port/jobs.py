from datetime import datetime
from typing import Protocol
from uuid import UUID


class ChannelsJobsProtocol(Protocol):
    """Планирует шаги в той же транзакции, что и бизнес-состояние."""

    async def verification(
        self,
        tenant_id: UUID,
        channel_id: UUID,
        job_id: UUID,
        generation: int,
        actor_id: UUID,
        now: datetime,
    ) -> None:
        """Идемпотентно регистрирует проверку без секретов в payload."""
        ...

    async def page(
        self, tenant_id: UUID, run_id: UUID, job_id: UUID, sequence: int, now: datetime
    ) -> None:
        """Идемпотентно регистрирует следующий шаг чтения."""
        ...

    async def is_recoverable(self, tenant_id: UUID, job_id: UUID) -> bool:
        """Проверяет возможность штатного выполнения/recovery фонового шага."""
        ...
