from src.modules.external_fulfillment.domain.value_object.supplier_reference import (
    ExternalSupplierReferenceVO,
)
from dataclasses import dataclass
from datetime import datetime

from src.modules.external_fulfillment.domain.draft_basis_snapshot import (
    SupplierFulfillmentAllocationSnapshot,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentOrderIdVO,
)
from src.modules.external_fulfillment.domain.value_object.line_binding import (
    SupplierFulfillmentLineBindingVO,
)
from src.modules.external_fulfillment.domain.value_object.line_confirmation import (
    SupplierFulfillmentLineConfirmationVO,
)
from src.modules.external_fulfillment.domain.value_object.plan_ref import (
    SupplierFulfillmentPlanRefVO,
)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentConfirmationSnapshot:
    """Передаёт исходный запрос и фактически принятое обязательство по каждой строке."""

    order_id: SupplierFulfillmentOrderIdVO
    order_version: int
    supplier: ExternalSupplierReferenceVO
    plan_ref: SupplierFulfillmentPlanRefVO
    requested_at: datetime
    confirmed_at: datetime
    allocations: tuple[SupplierFulfillmentAllocationSnapshot, ...]
    line_bindings: tuple[SupplierFulfillmentLineBindingVO, ...]
    line_confirmations: tuple[SupplierFulfillmentLineConfirmationVO, ...]
