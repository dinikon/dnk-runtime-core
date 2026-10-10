from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateTagResultDTO:
    """Подтверждённый результат конкретного сценария create_tag."""

    id: UUID
    revision: int
