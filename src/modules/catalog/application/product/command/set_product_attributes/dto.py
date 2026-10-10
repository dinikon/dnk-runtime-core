from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetProductAttributesResultDTO:
    """Результат конкретного сценария set_product_attributes."""

    id: UUID
    revision: int
