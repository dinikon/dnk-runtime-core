from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChangeProductTypeResultDTO:
    """Результат конкретного сценария change_product_type."""

    id: UUID
    revision: int
