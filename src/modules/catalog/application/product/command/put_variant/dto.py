from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutVariantResultDTO:
    id: UUID
    product_id: UUID
    sku_id: UUID
    sku_code: str
