from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.crm.domain.value_object.stage_snapshot import StageSnapshot


@dataclass(frozen=True, slots=True)
class PositionHistoryEntry:
    """Неизменяемый факт назначения или перемещения карточки."""

    id: UUID
    model_key: str
    record_id: UUID
    previous: StageSnapshot | None
    current: StageSnapshot
    previous_revision: int | None
    current_revision: int
    reason: str
    actor_id: UUID
    occurred_at: datetime


class PositionHistoryPort(Protocol):
    """Добавляет факты в общую транзакцию без самостоятельного commit."""

    async def append(self, entry: PositionHistoryEntry) -> None:
        """Сохраняет факт без изменения ранее записанной истории."""
        ...
