"""Безопасная проекция состояния запуска для Console."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SyncRunReadRow:
    """Не содержит checkpoint, секретов либо ответов площадок."""

    id: UUID
    config_revision: int
    revision: int
    status: str
    processed_count: int
    skipped_count: int
    pages_count: int
    automatic: bool
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    current_job_id: UUID
    recovery_required: bool = False


class SyncRunQueryRepository(Protocol):
    """Читает состояние без восстановления Domain-запуска."""

    async def latest(self, connection_id: UUID) -> SyncRunReadRow | None:
        """Возвращает последний запуск либо отсутствие запусков."""
        ...

    async def get(self, connection_id: UUID, run_id: UUID) -> SyncRunReadRow | None:
        """Читает запуск исключительно выбранного подключения."""
        ...
