from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateContentBlockResultDTO:
    """Результат конкретного сценария update_content_block."""

    id: UUID
    revision: int
