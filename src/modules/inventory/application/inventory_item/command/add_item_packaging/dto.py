from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AddItemPackagingResultDTO:
    """Передаёт созданный вариант упаковки товара."""

    id: UUID
    inventory_item_id: UUID
    packaging_type_id: UUID
    code: str
    name: str
    content_quantity: Decimal
    content_uom: str
