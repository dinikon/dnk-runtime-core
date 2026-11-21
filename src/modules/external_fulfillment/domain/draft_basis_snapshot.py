from src.modules.external_fulfillment.domain.value_object.supplier_reference import (
    ExternalSupplierReferenceVO,
)
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)
from src.modules.external_fulfillment.domain.time import (
    normalize_supplier_fulfillment_time,
)
from src.modules.external_fulfillment.domain.value_object.plan_ref import (
    SupplierFulfillmentPlanRefVO,
)
from src.modules.external_fulfillment.domain.value_object.quantity import (
    SupplierFulfillmentQuantityVO,
)
from src.modules.external_fulfillment.domain.value_object.references import (
    ExternalFulfillmentAllocationIdVO,
    ExternalInventoryItemIdVO,
    ExternalSupplierOfferIdVO,
    ExternalSupplierSourceIdVO,
)
from src.modules.external_fulfillment.domain.value_object.uom_code import (
    SupplierFulfillmentUomCodeVO,
)
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentAllocationSnapshot:
    """Передаёт выбранное целое плановое распределение с зафиксированной ценой."""

    allocation_id: ExternalFulfillmentAllocationIdVO
    inventory_item_id: ExternalInventoryItemIdVO
    supplier_source_id: ExternalSupplierSourceIdVO
    supplier_offer_id: ExternalSupplierOfferIdVO
    base_uom: SupplierFulfillmentUomCodeVO
    quantity: SupplierFulfillmentQuantityVO
    quoted_price: MoneyVO

    def ensure_valid(self) -> None:
        """Проверяет типизированные ссылки, положительное количество и цену распределения."""
        if (
            not isinstance(self.allocation_id, ExternalFulfillmentAllocationIdVO)
            or not isinstance(self.inventory_item_id, ExternalInventoryItemIdVO)
            or not isinstance(self.supplier_source_id, ExternalSupplierSourceIdVO)
            or not isinstance(self.supplier_offer_id, ExternalSupplierOfferIdVO)
            or not isinstance(self.base_uom, SupplierFulfillmentUomCodeVO)
            or not isinstance(self.quantity, SupplierFulfillmentQuantityVO)
            or self.quantity.value <= 0
            or not isinstance(self.quoted_price, MoneyVO)
            or not isinstance(self.quoted_price.amount, Decimal)
            or not self.quoted_price.amount.is_finite()
            or self.quoted_price.amount < 0
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Распределение требует типизированные ссылки, положительное количество и неотрицательную цену."
            )


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentPlanBasisSnapshot:
    """Хранит выбранные распределения одной версии плана на границе внешнего исполнения."""

    plan_ref: SupplierFulfillmentPlanRefVO
    plan_updated_at: datetime
    allocations: tuple[SupplierFulfillmentAllocationSnapshot, ...]

    def ensure_valid(self) -> None:
        """Требует непустой набор уникальных распределений и время основания в UTC."""
        if (
            not isinstance(self.plan_ref, SupplierFulfillmentPlanRefVO)
            or not isinstance(self.allocations, tuple)
            or not self.allocations
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужны ссылка на версию плана и непустой набор распределений."
            )
        normalize_supplier_fulfillment_time(self.plan_updated_at)
        if self.plan_updated_at.utcoffset() != timedelta(0):
            raise InvalidSupplierFulfillmentValueError(
                "Время основания плана должно храниться в UTC."
            )
        identifiers = set()
        for row in self.allocations:
            if not isinstance(row, SupplierFulfillmentAllocationSnapshot):
                raise InvalidSupplierFulfillmentValueError(
                    "Нужны снимки внешних распределений."
                )
            row.ensure_valid()
            if row.allocation_id in identifiers:
                raise InvalidSupplierFulfillmentValueError(
                    "Внешнее распределение выбрано дважды."
                )
            identifiers.add(row.allocation_id)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentSourceSnapshot:
    """Передаёт принадлежность и пригодность источника для прямой доставки."""

    id: ExternalSupplierSourceIdVO
    supplier: ExternalSupplierReferenceVO
    is_active: bool
    supports_dropship: bool

    def ensure_valid(self) -> None:
        """Проверяет идентичность источника и явные признаки маршрута."""
        if (
            not isinstance(self.id, ExternalSupplierSourceIdVO)
            or not isinstance(self.supplier, ExternalSupplierReferenceVO)
            or type(self.is_active) is not bool
            or type(self.supports_dropship) is not bool
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужны типизированные источник, поставщик и признаки прямой поставки."
            )


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentOfferSnapshot:
    """Передаёт идентичность предложения, его область, товар и базовую единицу."""

    id: ExternalSupplierOfferIdVO
    supplier: ExternalSupplierReferenceVO
    source_id: ExternalSupplierSourceIdVO | None
    inventory_item_id: ExternalInventoryItemIdVO
    base_uom: SupplierFulfillmentUomCodeVO
    is_active: bool

    def ensure_valid(self) -> None:
        """Проверяет номинальные ссылки, единицу и признак активности предложения."""
        if (
            not isinstance(self.id, ExternalSupplierOfferIdVO)
            or not isinstance(self.supplier, ExternalSupplierReferenceVO)
            or (
                self.source_id is not None
                and not isinstance(self.source_id, ExternalSupplierSourceIdVO)
            )
            or not isinstance(self.inventory_item_id, ExternalInventoryItemIdVO)
            or not isinstance(self.base_uom, SupplierFulfillmentUomCodeVO)
            or type(self.is_active) is not bool
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужны типизированные поля предложения для прямой поставки."
            )
