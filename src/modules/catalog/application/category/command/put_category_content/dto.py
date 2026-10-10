from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutCategoryContentResultDTO:
    """Подтверждённый результат конкретного сценария put_category_content."""

    id: UUID
    revision: int
