"""Намерение вручную получить актуальный список публикаций."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartSyncRunCommand:
    """Передаёт доверенный tenant и выбранный Channel."""

    tenant_id: UUID
    channel_id: UUID
