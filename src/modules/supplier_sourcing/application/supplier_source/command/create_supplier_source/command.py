from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from dataclasses import dataclass
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.application.supplier_source.stock_update_policy import (
    SupplierStockUpdatePolicyInput,
)


@dataclass(frozen=True, slots=True)
class CreateSupplierSourceCommand:
    """Передаёт явные настройки нового активного источника."""

    supplier: SupplierReferenceVO
    name: str
    fulfillment_modes: frozenset[SupplierFulfillmentMode]
    default_lead_time_seconds: int
    stock_update_policy: SupplierStockUpdatePolicyInput
    external_warehouse_code: str | None = None
