from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierModelKey,
)
from dataclasses import dataclass
from uuid import UUID
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)


@dataclass(frozen=True, slots=True)
class ListSupplierSourcesQuery:
    """Задаёт поиск, серверные фильтры и страницу справочника."""

    search: str | None = None
    supplier_model_key: SupplierModelKey | None = None
    supplier_id: UUID | None = None
    is_active: bool | None = None
    fulfillment_mode: SupplierFulfillmentMode | None = None
    offset: int = 0
    limit: int = 50
