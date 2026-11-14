from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierModelKey,
)
from dataclasses import dataclass
from uuid import UUID
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    StaleStockBehavior,
    MissingSkuBehavior,
)


@dataclass(frozen=True, slots=True)
class SupplierSourceListItemDTO:
    """Передаёт строку справочника без восстановления агрегата."""

    id: UUID
    supplier_model_key: SupplierModelKey
    supplier_id: UUID
    name: str
    external_warehouse_code: str | None
    fulfillment_modes: tuple[SupplierFulfillmentMode, ...]
    default_lead_time_seconds: int
    is_active: bool
    stock_ttl_seconds: int
    stale_behavior: StaleStockBehavior
    missing_sku_behavior: MissingSkuBehavior
    supplier_name: str | None = None


@dataclass(frozen=True, slots=True)
class ListSupplierSourcesResultDTO:
    """Передаёт страницу источников и общее количество по фильтрам."""

    items: tuple[SupplierSourceListItemDTO, ...]
    total: int
    offset: int
    limit: int
