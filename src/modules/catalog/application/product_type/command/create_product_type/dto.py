from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateProductTypeResultDTO:
    """Результат конкретного сценария create_product_type."""

    id: UUID
    revision: int
    schema_version: int
