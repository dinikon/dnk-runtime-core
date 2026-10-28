"""Результат принятого запроса синхронизации."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartSyncRunResultDTO:
    """Возвращает ID нового либо уже активного запуска."""

    id: UUID
    status: str
