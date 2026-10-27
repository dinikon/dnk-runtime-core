"""Узкий порт Channels к существующему Shared Jobs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VerificationJob:
    """Типизированное содержимое задания; секретов в нём нет."""

    tenant_id: UUID
    channel_id: UUID
    connection_id: UUID
    job_id: UUID
    config_revision: int


class VerificationJobs(Protocol):
    """Постановка, отмена и fencing в общей транзакции."""

    async def schedule(self, job: VerificationJob, now: datetime) -> None:
        """Планирует проверку в текущем UoW."""
        ...

    async def cancel(self, tenant_id: UUID, channel_id: UUID, now: datetime) -> None:
        """Отменяет все активные проверки подключения."""
        ...

    async def active(self, tenant_id: UUID, job_id: UUID) -> bool:
        """Проверяет существование scheduled/running задания."""
        ...

    async def inactive(self, tenant_id: UUID, job_ids: list[UUID]) -> set[UUID]:
        """Возвращает завершённые либо отсутствующие задания одной страницей."""
        ...

    async def owns(
        self, job: VerificationJob, lock_token: str, *, for_update: bool = False
    ) -> bool:
        """Проверяет актуальную lease, при необходимости блокируя строку."""
        ...
