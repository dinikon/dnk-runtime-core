from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateFunnelResultDTO:
    """Подтверждённый результат update процесса."""

    id: UUID
    revision: int
    stage_id_map: dict[str, UUID]
    moved_cards_count: int
