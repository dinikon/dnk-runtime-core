from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReplaceProductTypeSchemaResultDTO:
    """Результат конкретного сценария replace_product_type_schema."""

    id: UUID
    revision: int
    schema_version: int
