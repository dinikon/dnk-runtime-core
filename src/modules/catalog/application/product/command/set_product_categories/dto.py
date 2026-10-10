from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetProductCategoriesResultDTO:
    """Результат конкретного сценария set_product_categories."""

    id: UUID
    revision: int
