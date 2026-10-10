from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetProductTagsResultDTO:
    """Результат конкретного сценария set_product_tags."""

    id: UUID
    revision: int
