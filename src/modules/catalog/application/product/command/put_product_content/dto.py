from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutProductContentResultDTO:
    """Результат конкретного сценария put_product_content."""

    id: UUID
    revision: int
