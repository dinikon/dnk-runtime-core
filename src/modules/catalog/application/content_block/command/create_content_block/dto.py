from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateContentBlockResultDTO:
    """Результат конкретного сценария create_content_block."""

    id: UUID
    revision: int
