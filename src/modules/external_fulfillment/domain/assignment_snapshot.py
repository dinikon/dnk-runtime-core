from src.modules.external_fulfillment.domain.value_object.supplier_reference import (
    ExternalSupplierReferenceVO,
)
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.external_fulfillment.domain.draft_basis_snapshot import (
    SupplierFulfillmentAllocationSnapshot,
    SupplierFulfillmentPlanBasisSnapshot,
)
from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)
from src.modules.external_fulfillment.domain.time import (
    normalize_supplier_fulfillment_time,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentLineIdVO,
    SupplierFulfillmentOrderIdVO,
)
from src.modules.external_fulfillment.domain.value_object.line_binding import (
    SupplierFulfillmentLineBindingVO,
)
from src.modules.external_fulfillment.domain.value_object.plan_ref import (
    SupplierFulfillmentPlanRefVO,
)
from src.modules.external_fulfillment.domain.value_object.quantity_terms import (
    SupplierFulfillmentQuantityTermsVO,
)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentDraftSnapshot:
    """Передаёт состав и исходную версию черновика для закрепления в плане."""

    order_id: SupplierFulfillmentOrderIdVO
    order_version: int
    supplier: ExternalSupplierReferenceVO
    plan_ref: SupplierFulfillmentPlanRefVO
    created_at: datetime
    allocations: tuple[SupplierFulfillmentAllocationSnapshot, ...]
    line_bindings: tuple[SupplierFulfillmentLineBindingVO, ...]


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentAssignmentSnapshot:
    """Передаёт текущее закрепление всех строк внешнего заказа в плане."""

    order_id: SupplierFulfillmentOrderIdVO
    order_version: int
    supplier: ExternalSupplierReferenceVO
    source_plan_version: int
    assigned_at: datetime
    basis: SupplierFulfillmentPlanBasisSnapshot
    line_bindings: tuple[SupplierFulfillmentLineBindingVO, ...]
    quantity_terms: tuple[
        tuple[SupplierFulfillmentLineIdVO, SupplierFulfillmentQuantityTermsVO], ...
    ] = ()

    def ensure_valid(self) -> None:
        """Проверяет версии, время и типизированное полное основание закрепления."""
        if (
            not isinstance(self.order_id, SupplierFulfillmentOrderIdVO)
            or not isinstance(self.supplier, ExternalSupplierReferenceVO)
            or type(self.order_version) is not int
            or self.order_version < 0
            or type(self.source_plan_version) is not int
            or self.source_plan_version < 0
            or not isinstance(self.basis, SupplierFulfillmentPlanBasisSnapshot)
            or not isinstance(self.line_bindings, tuple)
            or any(
                not isinstance(binding, SupplierFulfillmentLineBindingVO)
                for binding in self.line_bindings
            )
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужно закрепление внешнего заказа с типизированными основанием, версиями и строками."
            )
        self.basis.ensure_valid()
        if not isinstance(self.quantity_terms, tuple) or any(
            not isinstance(entry, tuple)
            or len(entry) != 2
            or not isinstance(entry[0], SupplierFulfillmentLineIdVO)
            or not isinstance(entry[1], SupplierFulfillmentQuantityTermsVO)
            for entry in self.quantity_terms
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Правила количества должны быть привязаны к типизированным строкам."
            )
        if self.quantity_terms:
            line_ids = {line_id for line_id, _ in self.quantity_terms}
            if len(line_ids) != len(self.quantity_terms) or line_ids != {
                binding.line_id for binding in self.line_bindings
            }:
                raise InvalidSupplierFulfillmentValueError(
                    "Правила количества нужны для всех строк ровно по одному разу."
                )
        normalize_supplier_fulfillment_time(self.assigned_at)
        if (
            self.assigned_at.utcoffset() != timedelta(0)
            or self.assigned_at > self.basis.plan_updated_at
            or self.source_plan_version >= self.basis.plan_ref.plan_version
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Закрепление должно быть частью более новой версии плана с согласованным временем UTC."
            )
