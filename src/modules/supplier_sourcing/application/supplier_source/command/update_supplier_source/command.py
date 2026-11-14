from dataclasses import dataclass
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.application.supplier_source.stock_update_policy import (
    SupplierStockUpdatePolicyInput,
)


@dataclass(frozen=True, slots=True)
class UpdateSupplierSourceCommand:
    """Различает отсутствующее значение, null внешнего кода, false и нулевой срок."""

    source_id: SupplierSourceIdVO
    fields: frozenset[str]
    name: str | None = None
    external_warehouse_code: str | None = None
    fulfillment_modes: frozenset[SupplierFulfillmentMode] | None = None
    default_lead_time_seconds: int | None = None
    is_active: bool | None = None
    stock_update_policy: SupplierStockUpdatePolicyInput | None = None
