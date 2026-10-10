from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateAttributeResultDTO:
    """Подтверждённый результат конкретного сценария create_attribute."""

    id: UUID
    revision: int
