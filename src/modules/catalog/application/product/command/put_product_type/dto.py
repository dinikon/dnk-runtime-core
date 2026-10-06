from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutProductTypeResultDTO:
    product_id: UUID
    product_type_id: UUID
    schema_version: int
