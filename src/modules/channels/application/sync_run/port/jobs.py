"""Узкий порт доставки шагов синхронизации через Shared Jobs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SyncJob:
    """Передаёт идентификаторы поколения без конфигурации и секретов."""

    tenant_id: UUID
    channel_id: UUID
    connection_id: UUID
    run_id: UUID
    job_id: UUID
    config_revision: int


class PublicationSyncJobs(Protocol):
    """Работает на той же транзакции, что агрегаты Channels."""

    async def schedule(self, job: SyncJob, now: datetime) -> None:
        """Планирует один идемпотентный шаг."""
        ...

    async def cancel(self, tenant_id: UUID, run_id: UUID, now: datetime) -> None:
        """Инвалидирует задания запуска."""
        ...

    async def active(self, tenant_id: UUID, job_id: UUID) -> bool:
        """Отличает активное задание от terminal/missing."""
        ...

    async def owns(
        self, job: SyncJob, lock_token: str, *, for_update: bool = False
    ) -> bool:
        """Проверяет действующий lease, используя время БД."""
        ...
