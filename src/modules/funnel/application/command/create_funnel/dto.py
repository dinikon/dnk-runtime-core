from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateFunnelResultDTO:
    """Подтверждённый результат create процесса."""

    id: UUID
    revision: int
    stage_id_map: dict[str, UUID]
