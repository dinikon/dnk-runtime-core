from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
    EffectiveCatalogItemValues,
)


@dataclass(frozen=True, slots=True)
class CatalogItemReadDTO:
    """Компонент результата чтения, содержащий own/effective и версию корня."""

    root_id: UUID
    root_revision: int
    own: CatalogItemValuesSnapshot
    effective: EffectiveCatalogItemValues
    stock_status: str | None
    backorders_allowed: bool | None
    backordered: bool | None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    price_incomplete: bool = False
    price_currency: str | None = None
