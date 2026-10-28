"""Контекст доставки шага Shared Jobs."""

from dataclasses import dataclass

from src.modules.channels.application.sync_run.port.jobs import SyncJob


@dataclass(frozen=True, slots=True)
class PrepareSyncStepCommand:
    """Передаёт задание и текущий lease."""

    job: SyncJob
    lock_token: str
