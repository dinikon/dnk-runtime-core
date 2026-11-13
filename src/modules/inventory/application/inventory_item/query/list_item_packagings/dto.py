from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ItemPackagingListItemDTO:
    """Передаёт строку списка упаковок без восстановления Domain."""

    id: UUID
    inventory_item_id: UUID
    packaging_type_id: UUID
    code: str
    name: str
    content_quantity: Decimal
    content_uom: str


@dataclass(frozen=True, slots=True)
class ListItemPackagingsResultDTO:
    """Содержит страницу упаковок товара и общее число совпадений."""

    items: tuple[ItemPackagingListItemDTO, ...]
    total: int
    offset: int
    limit: int
