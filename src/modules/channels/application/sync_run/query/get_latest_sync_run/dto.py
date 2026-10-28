"""Результат конкретного сценария чтения запуска."""

from dataclasses import dataclass

from src.modules.channels.application.sync_run.port.query_repository import (
    SyncRunReadRow,
)


@dataclass(frozen=True, slots=True)
class GetLatestSyncRunResultDTO:
    """Передаёт безопасное состояние в Presentation."""

    sync_run: SyncRunReadRow | None
