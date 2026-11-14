from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_reference import (
    FulfillmentSupplierReferenceVO,
)
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentSupplierOrderAssignmentError,
    FulfillmentSupplierOrderConfirmationError,
    FulfillmentSupplierOrderRejectionError,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_basis_snapshot import (
    SupplierOrderAllocationSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierOrderIdVO,
    FulfillmentSupplierOrderLineIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_confirmation import (
    FulfillmentSupplierOrderConfirmationRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_rejection import (
    FulfillmentSupplierOrderRejectionRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_quantity_terms import (
    FulfillmentSupplierQuantityTermsVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


@dataclass(frozen=True, slots=True)
class SupplierOrderDraftLineSnapshot:
    """Связывает строку внешнего заказа с полными коммерческими условиями распределения."""

    line_id: FulfillmentSupplierOrderLineIdVO
    allocation: SupplierOrderAllocationSnapshot


@dataclass(frozen=True, slots=True)
class SupplierOrderDraftSnapshot:
    """Передаёт состав черновика поставщику для закрепления в плане."""

    order_id: FulfillmentSupplierOrderIdVO
    order_version: int
    supplier: FulfillmentSupplierReferenceVO
    plan_id: FulfillmentPlanIdVO
    source_plan_version: int
    created_at: datetime
    lines: tuple[SupplierOrderDraftLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет данные исходного черновика, его время и уникальные строки."""
        if (
            not isinstance(self.order_id, FulfillmentSupplierOrderIdVO)
            or type(self.order_version) is not int
            or self.order_version != 0
            or not isinstance(self.supplier, FulfillmentSupplierReferenceVO)
            or not isinstance(self.plan_id, FulfillmentPlanIdVO)
            or type(self.source_plan_version) is not int
            or self.source_plan_version < 0
        ):
            raise FulfillmentSupplierOrderAssignmentError(
                "Нужны идентичность черновика поставщику и версия исходного плана."
            )
        normalize_fulfillment_time(self.created_at)
        if self.created_at.utcoffset() != timedelta(0):
            raise FulfillmentSupplierOrderAssignmentError(
                "Время черновика должно храниться в UTC."
            )
        _ensure_lines(self.lines)


@dataclass(frozen=True, slots=True)
class SupplierOrderAssignmentSnapshot:
    """Передаёт полную группу закрепления из текущей версии плана."""

    plan_id: FulfillmentPlanIdVO
    plan_version: int
    plan_updated_at: datetime
    order_id: FulfillmentSupplierOrderIdVO
    order_version: int
    supplier: FulfillmentSupplierReferenceVO
    source_plan_version: int
    assigned_at: datetime
    lines: tuple[SupplierOrderDraftLineSnapshot, ...]
    quantity_terms: tuple[
        tuple[FulfillmentSupplierOrderLineIdVO, FulfillmentSupplierQuantityTermsVO], ...
    ] = ()

    def ensure_valid(self) -> None:
        """Проверяет ссылки, версии и хронологию закреплённой группы."""
        if (
            not isinstance(self.plan_id, FulfillmentPlanIdVO)
            or not isinstance(self.order_id, FulfillmentSupplierOrderIdVO)
            or not isinstance(self.supplier, FulfillmentSupplierReferenceVO)
            or type(self.plan_version) is not int
            or type(self.source_plan_version) is not int
            or not 0 <= self.source_plan_version < self.plan_version
            or type(self.order_version) is not int
            or self.order_version < 0
        ):
            raise FulfillmentSupplierOrderAssignmentError(
                "Закрепление требует более новую версию того же плана."
            )
        normalize_fulfillment_time(self.plan_updated_at)
        normalize_fulfillment_time(self.assigned_at)
        if (
            self.plan_updated_at.utcoffset() != timedelta(0)
            or self.assigned_at.utcoffset() != timedelta(0)
            or self.assigned_at > self.plan_updated_at
        ):
            raise FulfillmentSupplierOrderAssignmentError(
                "Закрепление должно относиться к истории текущего плана в UTC."
            )
        _ensure_lines(self.lines)
        if not isinstance(self.quantity_terms, tuple) or any(
            not isinstance(entry, tuple)
            or len(entry) != 2
            or not isinstance(entry[0], FulfillmentSupplierOrderLineIdVO)
            or not isinstance(entry[1], FulfillmentSupplierQuantityTermsVO)
            for entry in self.quantity_terms
        ):
            raise FulfillmentSupplierOrderAssignmentError(
                "Нужны типизированные правила количества и ссылки строк."
            )
        if self.quantity_terms:
            quantities = {line.line_id: line.allocation.quantity for line in self.lines}
            terms = dict(self.quantity_terms)
            if (
                len(terms) != len(self.quantity_terms)
                or terms.keys() != quantities.keys()
                or any(
                    not rule.accepts(quantities[line_id])
                    for line_id, rule in terms.items()
                )
            ):
                raise FulfillmentSupplierOrderAssignmentError(
                    "Правила должны соответствовать запрошенному количеству каждой строки."
                )


@dataclass(frozen=True, slots=True)
class SupplierOrderConfirmationSnapshot:
    """Передаёт подтверждение всей закреплённой группы по исходным условиям."""

    order_id: FulfillmentSupplierOrderIdVO
    supplier: FulfillmentSupplierReferenceVO
    plan_id: FulfillmentPlanIdVO
    source_plan_version: int
    confirmation: FulfillmentSupplierOrderConfirmationRefVO
    lines: tuple[SupplierOrderDraftLineSnapshot, ...]
    confirmed_quantities: (
        tuple[tuple[FulfillmentSupplierOrderLineIdVO, QuantityVO], ...] | None
    ) = None

    def ensure_valid(self) -> None:
        """Проверяет номинальные ссылки, исходную версию и полный состав снимка."""
        if (
            not isinstance(self.order_id, FulfillmentSupplierOrderIdVO)
            or not isinstance(self.supplier, FulfillmentSupplierReferenceVO)
            or not isinstance(self.plan_id, FulfillmentPlanIdVO)
            or type(self.source_plan_version) is not int
            or self.source_plan_version < 0
            or not isinstance(
                self.confirmation, FulfillmentSupplierOrderConfirmationRefVO
            )
        ):
            raise FulfillmentSupplierOrderConfirmationError(
                "Нужны ссылки подтверждённого заказа, плана и исходная версия."
            )
        self.confirmation.ensure_valid()
        try:
            _ensure_lines(self.lines)
        except FulfillmentSupplierOrderAssignmentError as exc:
            raise FulfillmentSupplierOrderConfirmationError(
                "Подтверждение требует уникальные строки одного источника."
            ) from exc
        if self.confirmed_quantities is None:
            return
        if not isinstance(self.confirmed_quantities, tuple) or any(
            not isinstance(entry, tuple)
            or len(entry) != 2
            or not isinstance(entry[0], FulfillmentSupplierOrderLineIdVO)
            or not isinstance(entry[1], QuantityVO)
            for entry in self.confirmed_quantities
        ):
            raise FulfillmentSupplierOrderConfirmationError(
                "Подтверждённые количества должны быть привязаны к строкам."
            )
        quantities = dict(self.confirmed_quantities)
        requested = {line.line_id: line.allocation.quantity for line in self.lines}
        if (
            len(quantities) != len(self.confirmed_quantities)
            or quantities.keys() != requested.keys()
            or any(
                quantity.value > requested[line_id].value
                for line_id, quantity in quantities.items()
            )
            or all(quantity.value.is_zero() for quantity in quantities.values())
        ):
            raise FulfillmentSupplierOrderConfirmationError(
                "Ответ требует все строки и хотя бы одно положительное количество в пределах запроса."
            )


@dataclass(frozen=True, slots=True)
class SupplierOrderRejectionSnapshot:
    """Передаёт отказ по полному составу закреплённого заказа."""

    order_id: FulfillmentSupplierOrderIdVO
    supplier: FulfillmentSupplierReferenceVO
    plan_id: FulfillmentPlanIdVO
    source_plan_version: int
    rejection: FulfillmentSupplierOrderRejectionRefVO
    lines: tuple[SupplierOrderDraftLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет ссылки отказа и уникальные строки одного источника."""
        if (
            not isinstance(self.order_id, FulfillmentSupplierOrderIdVO)
            or not isinstance(self.supplier, FulfillmentSupplierReferenceVO)
            or not isinstance(self.plan_id, FulfillmentPlanIdVO)
            or type(self.source_plan_version) is not int
            or self.source_plan_version < 0
            or not isinstance(self.rejection, FulfillmentSupplierOrderRejectionRefVO)
        ):
            raise FulfillmentSupplierOrderRejectionError(
                "Нужны ссылки отклонённого заказа, плана и исходная версия."
            )
        self.rejection.ensure_valid()
        try:
            _ensure_lines(self.lines)
        except FulfillmentSupplierOrderAssignmentError as exc:
            raise FulfillmentSupplierOrderRejectionError(
                "Отказ требует уникальные строки одного источника."
            ) from exc


def _ensure_lines(lines: tuple[SupplierOrderDraftLineSnapshot, ...]) -> None:
    """Требует целые уникальные распределения одного источника."""
    if not isinstance(lines, tuple) or not lines:
        raise FulfillmentSupplierOrderAssignmentError(
            "Нужен непустой tuple строк внешнего заказа."
        )
    allocations, line_ids, sources = set(), set(), set()
    for line in lines:
        if (
            not isinstance(line, SupplierOrderDraftLineSnapshot)
            or not isinstance(line.line_id, FulfillmentSupplierOrderLineIdVO)
            or not isinstance(line.allocation, SupplierOrderAllocationSnapshot)
        ):
            raise FulfillmentSupplierOrderAssignmentError(
                "Нужны типизированные снимки строк."
            )
        line.allocation.ensure_valid()
        if line.line_id in line_ids or line.allocation.id in allocations:
            raise FulfillmentSupplierOrderAssignmentError(
                "Строки и распределения должны быть уникальны."
            )
        line_ids.add(line.line_id)
        allocations.add(line.allocation.id)
        sources.add(line.allocation.source.supplier_source_id)
    if len(sources) != 1:
        raise FulfillmentSupplierOrderAssignmentError(
            "Группа должна относиться к одному источнику."
        )
