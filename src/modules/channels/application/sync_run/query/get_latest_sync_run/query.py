"""Параметры чтения состояния синхронизации."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetLatestSyncRunQuery:
    """Ограничивает чтение tenant и выбранным каналом."""

    tenant_id: UUID
    channel_id: UUID
