from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateSimpleProductResultDTO:
    """Результат конкретного сценария create_simple_product."""

    id: UUID
    revision: int
    variant_id: UUID
