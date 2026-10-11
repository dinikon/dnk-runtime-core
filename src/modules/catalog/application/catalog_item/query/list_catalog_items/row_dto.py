from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage


@dataclass(frozen=True, slots=True)
class CatalogItemListRowDTO:
    """Компактная строка списка без own частей редактора."""

    id: UUID
    kind: CatalogItemKind
    root_id: UUID
    root_revision: int
    revision: int
    status: CatalogItemStatus
    sku: str | None
    title: str | None
    price: Decimal | None
    currency: str | None
    price_min: Decimal | None
    price_max: Decimal | None
    price_incomplete: bool
    stock_status: str | None
    primary_image: CatalogItemImage | None
