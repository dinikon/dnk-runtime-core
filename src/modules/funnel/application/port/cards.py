from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FunnelStageSnapshotDTO:
    """Собственный межмодульный снимок определения стадии."""

    funnel_id: UUID
    stage_id: UUID
    funnel_name: str
    stage_name: str
    kind: str


class FunnelCardsPort(Protocol):
    """Изолирует Funnel от хранения и доменных объектов CRM."""

    async def counts(self, model_key: str, funnel_id: UUID) -> dict[UUID, int]:
        """Читает количества через контракт владельца карточек."""
        ...

    async def relocate(
        self,
        *,
        model_key: str,
        removed: tuple[FunnelStageSnapshotDTO, ...],
        target: FunnelStageSnapshotDTO,
        actor_id: UUID,
        now: datetime,
    ) -> int:
        """Переносит карточки в общей транзакции и возвращает их число."""
        ...
