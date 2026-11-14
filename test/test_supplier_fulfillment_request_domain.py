from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from src.modules.external_fulfillment.domain.value_object.supplier_reference import (
    ExternalSupplierReferenceVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_reference import (
    FulfillmentSupplierReferenceVO,
)

"""Закрепление внешнего заказа и проверяемая подготовка запроса поставщику."""

import unittest
from dataclasses import fields, replace
from datetime import UTC, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from test import test_inventory_fulfillment_progress_domain as progress_fixture
from test import test_supplier_fulfillment_order_domain as order_fixture
from src.modules.external_fulfillment.domain.aggregate import SupplierFulfillmentOrder
from src.modules.external_fulfillment.domain.assignment_snapshot import (
    SupplierFulfillmentAssignmentSnapshot,
)
from src.modules.external_fulfillment.domain.confirmation_snapshot import (
    SupplierFulfillmentConfirmationSnapshot,
)
from src.modules.external_fulfillment.domain.draft_basis_snapshot import (
    SupplierFulfillmentAllocationSnapshot,
    SupplierFulfillmentPlanBasisSnapshot,
)
from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
    SupplierFulfillmentBasisMismatchError,
    SupplierFulfillmentStatusError,
    SupplierFulfillmentTimeError,
    SupplierFulfillmentVersionConflictError,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentLineIdVO,
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
from src.modules.external_fulfillment.domain.value_object.quantity import (
    SupplierFulfillmentQuantityVO,
)
from src.modules.external_fulfillment.domain.value_object.quantity_terms import (
    SupplierFulfillmentQuantityTermsVO,
)
from src.modules.external_fulfillment.domain.value_object.references import (
    ExternalFulfillmentAllocationIdVO,
    ExternalFulfillmentPlanIdVO,
    ExternalInventoryItemIdVO,
    ExternalSupplierIdVO,
    ExternalSupplierOfferIdVO,
    ExternalSupplierSourceIdVO,
)
from src.modules.external_fulfillment.domain.value_object.status import (
    SupplierFulfillmentOrderStatus,
)
from src.modules.external_fulfillment.domain.value_object.uom_code import (
    SupplierFulfillmentUomCodeVO,
)
from src.modules.inventory.domain.error import QuantityStepError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentAllocationCancellationConflictError,
    FulfillmentDemandExceededError,
    FulfillmentPlanContextError,
    FulfillmentPlanStatusError,
    FulfillmentPlanTimeError,
    FulfillmentPlanVersionConflictError,
    FulfillmentSupplierOrderAssignmentError,
    FulfillmentSupplierOrderConfirmationError,
    FulfillmentSupplierOrderRejectionError,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_assignment_snapshot import (
    SupplierOrderDraftLineSnapshot,
    SupplierOrderDraftSnapshot,
    SupplierOrderConfirmationSnapshot,
    SupplierOrderRejectionSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_basis_snapshot import (
    SupplierOrderAllocationSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_confirmation import (
    FulfillmentSupplierOrderConfirmationRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_rejection import (
    FulfillmentSupplierOrderRejectionRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_dropship_source_ref import (
    SupplierDropshipSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierIdVO,
    FulfillmentSupplierOfferIdVO,
    FulfillmentSupplierOrderIdVO,
    FulfillmentSupplierOrderLineIdVO,
    FulfillmentSupplierSourceIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentAllocationError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class SupplierFulfillmentRequestDomainTests(unittest.TestCase):
    """Проверяет оба агрегата через снимки на границе прямого исполнения."""

    def setUp(self) -> None:
        """Готовит DRAFT на 4 PCS поставщика из смешанного плана на 7 PCS."""
        self.f = order_fixture.SupplierFulfillmentOrderDomainTests()
        self.f.setUp()
        self.plan = self.f.planned
        self.order = self.f.create()
        self.at = self.order.created_at + timedelta(minutes=1)

    def inventory_draft(
        self, order: SupplierFulfillmentOrder
    ) -> SupplierOrderDraftSnapshot:
        """Переводит экспорт черновика в локальные номинальные ссылки Inventory."""
        draft = order.draft_snapshot()
        return SupplierOrderDraftSnapshot(
            order_id=FulfillmentSupplierOrderIdVO(draft.order_id.uuid),
            order_version=draft.order_version,
            supplier=FulfillmentSupplierReferenceVO.from_value(
                draft.supplier.model_key.value, draft.supplier.identifier.uuid
            ),
            plan_id=FulfillmentPlanIdVO(draft.plan_ref.plan_id.uuid),
            source_plan_version=draft.plan_ref.plan_version,
            created_at=draft.created_at,
            lines=self.inventory_lines(draft.allocations, draft.line_bindings),
        )

    def inventory_lines(
        self,
        allocations: tuple[SupplierFulfillmentAllocationSnapshot, ...],
        line_bindings: tuple[SupplierFulfillmentLineBindingVO, ...],
    ) -> tuple[SupplierOrderDraftLineSnapshot, ...]:
        """Переводит целые строки внешнего заказа в локальные снимки Inventory."""
        bindings = {binding.allocation_id: binding.line_id for binding in line_bindings}
        return tuple(
            SupplierOrderDraftLineSnapshot(
                FulfillmentSupplierOrderLineIdVO(bindings[row.allocation_id].uuid),
                SupplierOrderAllocationSnapshot(
                    id=FulfillmentAllocationIdVO(row.allocation_id.uuid),
                    source=SupplierDropshipSourceRefVO(
                        FulfillmentSupplierSourceIdVO(row.supplier_source_id.uuid),
                        FulfillmentSupplierOfferIdVO(row.supplier_offer_id.uuid),
                    ),
                    inventory_item_id=InventoryItemIdVO(row.inventory_item_id.uuid),
                    base_uom=UomCodeVO(row.base_uom.value),
                    quantity=QuantityVO(row.quantity.value),
                    quoted_purchase_price=row.quoted_price,
                ),
            )
            for row in allocations
        )

    def assign(
        self,
        plan: FulfillmentPlan | None = None,
        order: SupplierFulfillmentOrder | None = None,
        **changes: object,
    ) -> FulfillmentPlan:
        """Закрепляет полный снимок черновика по текущим товарам и предложениям."""
        target = self.plan if plan is None else plan
        draft = self.order if order is None else order
        return target.assign_supplier_order(
            **(
                dict(
                    draft=self.inventory_draft(draft),
                    demand=self.f.f.f.demand,
                    inventory_items=(self.f.f.f.item,),
                    supplier_options=(self.f.f.option,),
                    expected_version=target.version,
                    updated_at=max(self.at, target.updated_at),
                )
                | changes
            )
        )

    def external_assignment(
        self, plan: FulfillmentPlan, order: SupplierFulfillmentOrder
    ) -> SupplierFulfillmentAssignmentSnapshot:
        """Передаёт реальную закреплённую группу в контрактах внешнего исполнения."""
        assignment = plan.supplier_order_assignment_snapshot(
            order_id=FulfillmentSupplierOrderIdVO(order.id.uuid)
        )
        return SupplierFulfillmentAssignmentSnapshot(
            order_id=SupplierFulfillmentOrderIdVO(assignment.order_id.uuid),
            order_version=assignment.order_version,
            supplier=ExternalSupplierReferenceVO.from_value(
                assignment.supplier.model_key.value, assignment.supplier.identifier.uuid
            ),
            source_plan_version=assignment.source_plan_version,
            assigned_at=assignment.assigned_at,
            basis=SupplierFulfillmentPlanBasisSnapshot(
                plan_ref=SupplierFulfillmentPlanRefVO(
                    ExternalFulfillmentPlanIdVO(assignment.plan_id.uuid),
                    assignment.plan_version,
                ),
                plan_updated_at=assignment.plan_updated_at,
                allocations=tuple(
                    SupplierFulfillmentAllocationSnapshot(
                        allocation_id=ExternalFulfillmentAllocationIdVO(
                            row.allocation.id.uuid
                        ),
                        inventory_item_id=ExternalInventoryItemIdVO(
                            row.allocation.inventory_item_id.uuid
                        ),
                        supplier_source_id=ExternalSupplierSourceIdVO(
                            row.allocation.source.supplier_source_id.uuid
                        ),
                        supplier_offer_id=ExternalSupplierOfferIdVO(
                            row.allocation.source.supplier_offer_id.uuid
                        ),
                        base_uom=SupplierFulfillmentUomCodeVO(
                            row.allocation.base_uom.value
                        ),
                        quantity=SupplierFulfillmentQuantityVO(
                            row.allocation.quantity.value
                        ),
                        quoted_price=row.allocation.quoted_purchase_price,
                    )
                    for row in assignment.lines
                ),
            ),
            line_bindings=tuple(
                SupplierFulfillmentLineBindingVO(
                    ExternalFulfillmentAllocationIdVO(row.allocation.id.uuid),
                    SupplierFulfillmentLineIdVO(row.line_id.uuid),
                )
                for row in assignment.lines
            ),
            quantity_terms=tuple(
                (
                    SupplierFulfillmentLineIdVO(line_id.uuid),
                    SupplierFulfillmentQuantityTermsVO(
                        rule.step, rule.minimum, rule.multiple
                    ),
                )
                for line_id, rule in assignment.quantity_terms
            ),
        )

    def two_lines(self) -> tuple[FulfillmentPlan, SupplierFulfillmentOrder]:
        """Строит две внешние строки одного предложения для разных строк потребности."""
        another = FulfillmentAllocationIdVO(uuid4())
        draft = self.f.f.add(
            self.f.draft, identifier=another, source_ref=self.f.f.f.other_ref
        )
        planned = self.f.f.mark(draft)
        basis = self.f.map_basis(planned, self.f.allocation_id, another)
        return planned, self.f.create(basis=basis, line_bindings=self.f.bindings(basis))

    def test_assigns_whole_order_and_requests_without_confirming_allocations(
        self,
    ) -> None:
        """Запрос готов после полного закрепления, внешняя строка остаётся PLANNED."""
        assigned = self.assign()
        row = assigned.get_allocation(self.f.allocation_id)
        self.assertEqual(assigned.version, self.plan.version + 1)
        self.assertIs(assigned.status, self.plan.status)
        self.assertIs(row.status, FulfillmentAllocationStatus.PLANNED)
        self.assertIsNone(row.reservation)
        self.assertEqual(
            row.supplier_order_assignment.order_id.uuid, self.order.id.uuid
        )
        self.assertEqual(
            row.supplier_order_assignment.line_id.uuid, self.order.lines[0].id.uuid
        )
        self.assertIsNone(
            self.plan.get_allocation(self.f.allocation_id).supplier_order_assignment
        )
        assignment = self.external_assignment(assigned, self.order)
        requested = self.order.request(
            assignment,
            expected_version=0,
            requested_at=self.at.astimezone(timezone(timedelta(hours=2))),
        )
        self.assertIs(requested.status, SupplierFulfillmentOrderStatus.REQUESTED)
        self.assertEqual(requested.version, 1)
        self.assertEqual(requested.requested_at, self.at)
        self.assertIs(requested.requested_at.tzinfo, UTC)
        self.assertEqual(
            tuple(replace(line, quantity_terms=None) for line in requested.lines),
            self.order.lines,
        )
        self.assertEqual(
            requested.lines[0].quantity_terms,
            SupplierFulfillmentQuantityTermsVO(Decimal(1), Decimal(2), Decimal(2)),
        )
        self.assertEqual(requested.plan_ref, self.order.plan_ref)
        self.assertIs(self.order.status, SupplierFulfillmentOrderStatus.DRAFT)
        self.assertEqual(self.f.restore(requested), requested)

    def test_competing_order_and_changed_replay_cannot_take_assignment(self) -> None:
        """Один черновик закрепляет строку, точный повтор сохраняет первую версию назначения."""
        assigned = self.assign()
        self.assertIs(
            self.assign(assigned, updated_at=self.at + timedelta(minutes=1)), assigned
        )
        with self.assertRaises(FulfillmentSupplierOrderAssignmentError):
            self.assign(assigned, self.f.create())
        draft = self.inventory_draft(self.order)
        changed_line = replace(
            draft.lines[0], line_id=FulfillmentSupplierOrderLineIdVO(uuid4())
        )
        with self.assertRaises(FulfillmentSupplierOrderAssignmentError):
            self.assign(assigned, draft=replace(draft, lines=(changed_line,)))

    def test_assignment_blocks_cancel_and_new_draft_export(self) -> None:
        """Закреплённое распределение нельзя отменить через обычные складские переходы."""
        assigned = self.assign()
        with self.assertRaises(FulfillmentAllocationCancellationConflictError):
            assigned.cancel_allocations(
                allocation_ids=(self.f.allocation_id,),
                expected_version=assigned.version,
                updated_at=self.at,
            )
        with self.assertRaises(FulfillmentSupplierOrderAssignmentError):
            assigned.cancel(expected_version=assigned.version, updated_at=self.at)
        with self.assertRaises(FulfillmentPlanContextError):
            assigned.supplier_order_basis_snapshot(
                allocation_ids=(self.f.allocation_id,)
            )

    def test_assignment_rechecks_price_terms_mode_activity_and_current_quantity_step(
        self,
    ) -> None:
        """Условия от момента планирования могут устареть перед закреплением."""
        option = self.f.f.option
        for changes, error in (
            (
                dict(purchase_price=MoneyVO(Decimal(130), CurrencyVO("UAH"))),
                FulfillmentPlanContextError,
            ),
            (dict(source_supports_dropship=False), FulfillmentPlanContextError),
            (dict(offer_is_active=False), FulfillmentPlanContextError),
            (
                dict(min_order_qty=QuantityVO(Decimal(5))),
                InvalidFulfillmentAllocationError,
            ),
            (
                dict(order_multiple=QuantityVO(Decimal(3))),
                InvalidFulfillmentAllocationError,
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(error):
                self.assign(supplier_options=(replace(option, **changes),))
        item = replace(self.f.f.f.item, quantity_rules=QuantityRulesVO(Decimal(3)))
        with self.assertRaises(QuantityStepError):
            self.assign(inventory_items=(item,))
        self.assertIsNone(
            self.plan.get_allocation(self.f.allocation_id).supplier_order_assignment
        )

    def test_older_draft_is_requestable_after_warehouse_shipment(self) -> None:
        """Рост версии из-за складской отгрузки не меняет внешнее основание."""
        confirmed = self.f.f.confirm_warehouse(self.plan)
        draft = self.f.f.shipments.create(
            fulfillment_plan=confirmed.shipment_snapshot()
        )
        assigned_shipment, shipment = self.f.f.shipments.assign_and_confirm(
            confirmed, draft
        )
        progress = progress_fixture.FulfillmentProgressDomainTests()
        progress.setUp()
        shipped = progress.execute(shipment, {shipment.lines[0].id: "3"}, at=self.at)
        after = progress.register(assigned_shipment, shipped)
        original_demand = self.f.f.f.demand
        remaining = replace(
            original_demand,
            lines=(
                replace(original_demand.lines[0], remaining_qty=QuantityVO(Decimal(4))),
                *original_demand.lines[1:],
            ),
        )
        assigned = self.assign(after, demand=remaining)
        requested = self.order.request(
            self.external_assignment(assigned, self.order),
            expected_version=0,
            requested_at=self.at,
        )
        self.assertIs(requested.status, SupplierFulfillmentOrderStatus.REQUESTED)
        self.assertIs(assigned.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertEqual(requested.plan_ref.plan_version, self.plan.version)

    def test_rejects_foreign_plan_cancelled_or_changed_allocation_and_future_basis(
        self,
    ) -> None:
        """Снимок черновика не заменяет проверку актуального состава плана."""
        draft = self.inventory_draft(self.order)
        for changed in (
            replace(draft, plan_id=FulfillmentPlanIdVO(uuid4())),
            replace(draft, source_plan_version=self.plan.version + 1),
            replace(
                draft,
                supplier=FulfillmentSupplierReferenceVO.from_value(
                    "crm.company", uuid4()
                ),
            ),
            replace(
                draft,
                lines=(
                    replace(
                        draft.lines[0],
                        allocation=replace(
                            draft.lines[0].allocation, quantity=QuantityVO(Decimal(2))
                        ),
                    ),
                ),
            ),
        ):
            with (
                self.subTest(changed=changed),
                self.assertRaises(FulfillmentSupplierOrderAssignmentError),
            ):
                self.assign(draft=changed)
        cancelled = self.plan.cancel_allocations(
            allocation_ids=(self.f.allocation_id,),
            expected_version=self.plan.version,
            updated_at=self.at,
        )
        with self.assertRaises(FulfillmentSupplierOrderAssignmentError):
            self.assign(cancelled)

    def test_requires_full_group_for_replay_and_request(self) -> None:
        """Пропуск одной из двух строк отклоняется при закреплении и перед запросом."""
        plan, order = self.two_lines()
        assigned = self.assign(plan, order)
        self.assertEqual(assigned.version, plan.version + 1)
        proof = self.external_assignment(assigned, order)
        self.assertEqual(len(proof.basis.allocations), 2)
        draft = self.inventory_draft(order)
        with self.assertRaises(FulfillmentSupplierOrderAssignmentError):
            self.assign(assigned, order, draft=replace(draft, lines=draft.lines[:1]))
        partial = replace(
            proof,
            basis=replace(proof.basis, allocations=proof.basis.allocations[:1]),
            line_bindings=proof.line_bindings[:1],
            quantity_terms=proof.quantity_terms[:1],
        )
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            order.request(partial, expected_version=0, requested_at=self.at)
        self.assertIs(
            order.request(proof, expected_version=0, requested_at=self.at).status,
            SupplierFulfillmentOrderStatus.REQUESTED,
        )

    def test_request_rejects_other_order_supplier_or_changed_bindings_and_facts(
        self,
    ) -> None:
        """Запрос сравнивает заказ, поставщика, версию, условия и соответствия каждой строки."""
        proof = self.external_assignment(self.assign(), self.order)
        binding = proof.line_bindings[0]
        row = proof.basis.allocations[0]
        for changed in (
            replace(proof, order_id=SupplierFulfillmentOrderIdVO(uuid4())),
            replace(
                proof,
                supplier=ExternalSupplierReferenceVO.from_value("crm.company", uuid4()),
            ),
            replace(proof, order_version=1),
            replace(proof, source_plan_version=proof.source_plan_version - 1),
            replace(
                proof,
                line_bindings=(
                    replace(binding, line_id=SupplierFulfillmentLineIdVO(uuid4())),
                ),
                quantity_terms=(),
            ),
            replace(
                proof,
                basis=replace(
                    proof.basis,
                    allocations=(
                        replace(
                            row, quantity=SupplierFulfillmentQuantityVO(Decimal(2))
                        ),
                    ),
                ),
            ),
        ):
            with (
                self.subTest(changed=changed),
                self.assertRaises(SupplierFulfillmentBasisMismatchError),
            ):
                self.order.request(changed, expected_version=0, requested_at=self.at)

    def test_request_version_time_and_repeat_are_checked(self) -> None:
        """Запрос требует актуальную версию, время закрепления и состояние DRAFT."""
        proof = self.external_assignment(self.assign(), self.order)
        with self.assertRaises(SupplierFulfillmentVersionConflictError):
            self.order.request(proof, expected_version=1, requested_at=self.at)
        with self.assertRaises(SupplierFulfillmentTimeError):
            self.order.request(
                proof, expected_version=0, requested_at=self.at - timedelta(seconds=1)
            )
        requested = self.order.request(proof, expected_version=0, requested_at=self.at)
        with self.assertRaises(SupplierFulfillmentStatusError):
            requested.request(proof, expected_version=1, requested_at=self.at)
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            self.f.restore(requested, requested_at=None)

    def test_restore_rejects_inconsistent_assignment_group(self) -> None:
        """План восстанавливает связи одной группы с уникальными внешними строками."""
        plan, order = self.two_lines()
        assigned = self.assign(plan, order)
        values = {
            field.name: getattr(assigned, field.name) for field in fields(assigned)
        }
        values["identifier"] = values.pop("id")
        self.assertEqual(FulfillmentPlan.restore(**values), assigned)
        warehouse, first, second = assigned.allocations
        for assignment in (
            replace(
                second.supplier_order_assignment,
                line_id=first.supplier_order_assignment.line_id,
            ),
            replace(
                second.supplier_order_assignment,
                assigned_at=self.at + timedelta(seconds=1),
            ),
            replace(
                second.supplier_order_assignment,
                supplier=FulfillmentSupplierReferenceVO.from_value(
                    "crm.company", uuid4()
                ),
            ),
        ):
            with (
                self.subTest(assignment=assignment),
                self.assertRaises(FulfillmentSupplierOrderAssignmentError),
            ):
                FulfillmentPlan.restore(
                    **(
                        values
                        | dict(
                            allocations=(
                                warehouse,
                                first,
                                replace(second, supplier_order_assignment=assignment),
                            )
                        )
                    )
                )

    def test_rechecks_remaining_order_demand_before_assignment(self) -> None:
        """Уменьшившаяся потребность ограничивает общий состав смешанного плана."""
        original = self.f.f.f.demand
        reduced = replace(
            original,
            lines=(
                replace(original.lines[0], remaining_qty=QuantityVO(Decimal(6))),
                *original.lines[1:],
            ),
        )
        with self.assertRaises(FulfillmentDemandExceededError):
            self.assign(demand=reduced)

    def request_order(
        self, assigned: FulfillmentPlan, draft: SupplierFulfillmentOrder | None = None
    ) -> SupplierFulfillmentOrder:
        """Готовит запрос из закреплённой в плане группы."""
        order = self.order if draft is None else draft
        return order.request(
            self.external_assignment(assigned, order),
            expected_version=order.version,
            requested_at=max(assigned.updated_at, self.at),
        )

    @staticmethod
    def supplier_reply(
        order: SupplierFulfillmentOrder,
    ) -> tuple[SupplierFulfillmentLineConfirmationVO, ...]:
        """Формирует ответ по всем исходным условиям запроса."""
        return tuple(
            SupplierFulfillmentLineConfirmationVO(
                line.id, line.requested_quantity, line.quoted_price
            )
            for line in order.lines
        )

    def inventory_confirmation(
        self, order: SupplierFulfillmentOrder
    ) -> SupplierOrderConfirmationSnapshot:
        """Передаёт экспорт подтверждённого заказа в типах Inventory."""
        return self.map_confirmation(order.confirmation_snapshot())

    def map_confirmation(
        self, snapshot: SupplierFulfillmentConfirmationSnapshot
    ) -> SupplierOrderConfirmationSnapshot:
        """Переводит подтверждение поставщика в контракт принимающего модуля."""
        return SupplierOrderConfirmationSnapshot(
            order_id=FulfillmentSupplierOrderIdVO(snapshot.order_id.uuid),
            supplier=FulfillmentSupplierReferenceVO.from_value(
                snapshot.supplier.model_key.value, snapshot.supplier.identifier.uuid
            ),
            plan_id=FulfillmentPlanIdVO(snapshot.plan_ref.plan_id.uuid),
            source_plan_version=snapshot.plan_ref.plan_version,
            confirmation=FulfillmentSupplierOrderConfirmationRefVO(
                snapshot.order_version, snapshot.requested_at, snapshot.confirmed_at
            ),
            lines=self.inventory_lines(snapshot.allocations, snapshot.line_bindings),
            confirmed_quantities=tuple(
                (
                    FulfillmentSupplierOrderLineIdVO(line.line_id.uuid),
                    QuantityVO(line.quantity.value),
                )
                for line in snapshot.line_confirmations
            ),
        )

    def register_confirmation(
        self, plan: FulfillmentPlan, snapshot: SupplierOrderConfirmationSnapshot
    ) -> FulfillmentPlan:
        """Регистрирует ответ в текущей версии плана."""
        return plan.register_supplier_confirmation(
            snapshot,
            expected_version=plan.version,
            updated_at=max(plan.updated_at, snapshot.confirmation.confirmed_at),
        )

    def test_full_confirmation_before_warehouse_shipment(self) -> None:
        """Резерв и ответ поставщика подтверждают план, но только склад попадает в Shipment."""
        mixed = self.f.f.confirm_warehouse(self.plan)
        assigned = self.assign(mixed)
        requested = self.request_order(assigned)
        confirmed = requested.confirm(
            self.supplier_reply(requested),
            expected_version=1,
            confirmed_at=self.at.astimezone(timezone(timedelta(hours=2))),
        )
        self.assertIs(confirmed.status, SupplierFulfillmentOrderStatus.CONFIRMED)
        self.assertEqual(confirmed.version, 2)
        self.assertIs(confirmed.confirmed_at.tzinfo, UTC)
        self.assertEqual(confirmed.confirmed_at, self.at)
        self.assertEqual(
            confirmed.lines[0].confirmed_quantity, requested.lines[0].requested_quantity
        )
        self.assertEqual(
            confirmed.lines[0].confirmed_price, requested.lines[0].quoted_price
        )
        self.assertIsNone(requested.lines[0].confirmed_quantity)
        self.assertEqual(self.f.restore(confirmed), confirmed)
        snapshot = self.inventory_confirmation(confirmed)
        plan = self.register_confirmation(assigned, snapshot)
        self.assertEqual(plan.version, assigned.version + 1)
        self.assertIs(plan.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertTrue(plan.is_fully_confirmed())
        self.assertEqual(
            plan.remaining_to_allocate(self.f.f.f.line_ref, demand=self.f.f.f.demand),
            QuantityVO(Decimal(0)),
        )
        external = plan.get_allocation(self.f.allocation_id)
        self.assertEqual(external.supplier_confirmation, snapshot.confirmation)
        self.assertIs(external.status, FulfillmentAllocationStatus.CONFIRMED)
        self.assertEqual(external.fulfilled_qty, QuantityVO(Decimal(0)))
        self.assertIsNone(external.reservation)
        shipment = self.f.f.shipments.create(
            fulfillment_plan=plan.shipment_snapshot(), created_at=plan.updated_at
        )
        self.assertEqual(len(shipment.lines), 1)
        self.assertNotEqual(shipment.lines[0].fulfillment_allocation_id, external.id)
        with_shipment, ready = self.f.f.shipments.assign_and_confirm(plan, shipment)
        progress = progress_fixture.FulfillmentProgressDomainTests()
        progress.setUp()
        shipped = progress.execute(
            ready, {ready.lines[0].id: "3"}, at=self.at + timedelta(minutes=1)
        )
        after = progress.register(with_shipment, shipped)
        self.assertIs(after.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertTrue(after.is_fully_confirmed())
        self.assertEqual(after.get_allocation(external.id), external)

    def test_supplier_confirmation_after_warehouse_shipment(self) -> None:
        """Более поздняя регистрация ответа сохраняет уже зарегистрированные 3 PCS склада."""
        assigned = self.assign(self.f.f.confirm_warehouse(self.plan))
        requested = self.request_order(assigned)
        draft = self.f.f.shipments.create(
            fulfillment_plan=assigned.shipment_snapshot(),
            created_at=assigned.updated_at,
        )
        with_shipment, shipment = self.f.f.shipments.assign_and_confirm(assigned, draft)
        progress = progress_fixture.FulfillmentProgressDomainTests()
        progress.setUp()
        shipped = progress.execute(
            shipment, {shipment.lines[0].id: "3"}, at=self.at + timedelta(minutes=1)
        )
        after = progress.register(with_shipment, shipped)
        for confirmed_at in (self.at, after.updated_at):
            with self.subTest(confirmed_at=confirmed_at):
                confirmed = requested.confirm(
                    self.supplier_reply(requested),
                    expected_version=1,
                    confirmed_at=confirmed_at,
                )
                result = self.register_confirmation(
                    after, self.inventory_confirmation(confirmed)
                )
                self.assertIs(result.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
                self.assertTrue(result.is_fully_confirmed())
                self.assertEqual(result.allocations[0], after.allocations[0])
                self.assertEqual(
                    result.allocations[0].fulfilled_qty, QuantityVO(Decimal(3))
                )
                result.shipment_snapshot().ensure_valid()
                self.assertEqual(progress.restore(result), result)

    def test_supplier_can_confirm_before_warehouse_reservation(self) -> None:
        """Складское подтверждение учитывает уже подтверждённую внешнюю часть."""
        assigned = self.assign()
        requested = self.request_order(assigned)
        confirmed = requested.confirm(
            self.supplier_reply(requested), expected_version=1, confirmed_at=self.at
        )
        result = self.register_confirmation(
            assigned, self.inventory_confirmation(confirmed)
        )
        self.assertIs(result.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertFalse(result.is_fully_confirmed())
        result.shipment_snapshot().ensure_valid()
        mixed = self.f.f.confirm_warehouse(
            result, updated_at=max(result.updated_at, self.f.f.shipments.at)
        )
        self.assertIs(mixed.status, FulfillmentPlanStatus.CONFIRMED)
        supplier_only = result.cancel_allocations(
            allocation_ids=(result.allocations[0].id,),
            expected_version=result.version,
            updated_at=result.updated_at,
        )
        self.assertIs(supplier_only.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertTrue(supplier_only.is_fully_confirmed())

    def test_confirms_all_lines_once_and_validates_restore(self) -> None:
        """Полный ответ с любым порядком строк регистрируется одной версией обоих агрегатов."""
        plan, draft = self.two_lines()
        assigned = self.assign(plan, draft)
        requested = self.request_order(assigned, draft)
        reply = self.supplier_reply(requested)
        confirmed = requested.confirm(
            reply[::-1], expected_version=1, confirmed_at=self.at
        )
        self.assertIs(
            confirmed.confirm(reply, expected_version=2, confirmed_at=self.at),
            confirmed,
        )
        snapshot = self.inventory_confirmation(confirmed)
        registered = self.register_confirmation(assigned, snapshot)
        self.assertEqual(registered.version, assigned.version + 1)
        self.assertEqual(
            sum(
                row.supplier_confirmation is not None for row in registered.allocations
            ),
            2,
        )
        self.assertIs(
            self.register_confirmation(
                registered, replace(snapshot, lines=snapshot.lines[::-1])
            ),
            registered,
        )
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            confirmed.confirm(
                reply, expected_version=2, confirmed_at=self.at + timedelta(seconds=1)
            )
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            self.f.restore(confirmed, lines=(requested.lines[0], confirmed.lines[1]))
        values = {
            field.name: getattr(registered, field.name) for field in fields(registered)
        }
        values["identifier"] = values.pop("id")
        self.assertEqual(FulfillmentPlan.restore(**values), registered)
        with self.assertRaises(FulfillmentSupplierOrderAssignmentError):
            FulfillmentPlan.restore(
                **(
                    values
                    | dict(
                        allocations=(
                            *registered.allocations[:-1],
                            assigned.allocations[-1],
                        )
                    )
                )
            )

    def test_rejects_incomplete_duplicate_or_changed_supplier_reply(self) -> None:
        """Ответ покрывает все строки в пределах запроса и сохраняет цену и валюту."""
        plan, draft = self.two_lines()
        requested = self.request_order(self.assign(plan, draft), draft)
        first, second = self.supplier_reply(requested)
        for reply in (
            (first,),
            (first, second, second),
            (replace(first, line_id=SupplierFulfillmentLineIdVO(uuid4())), second),
            (
                replace(first, quantity=SupplierFulfillmentQuantityVO(Decimal(3))),
                second,
            ),
            (
                replace(first, quantity=SupplierFulfillmentQuantityVO(Decimal(6))),
                second,
            ),
            (replace(first, price=MoneyVO(Decimal(1), first.price.currency)), second),
            (
                replace(first, price=MoneyVO(first.price.amount, CurrencyVO("USD"))),
                second,
            ),
        ):
            with (
                self.subTest(reply=reply),
                self.assertRaises(SupplierFulfillmentBasisMismatchError),
            ):
                requested.confirm(reply, expected_version=1, confirmed_at=self.at)
        self.assertIs(requested.status, SupplierFulfillmentOrderStatus.REQUESTED)

    def test_register_requires_same_whole_group_and_commercial_terms(self) -> None:
        """Ни чужой ответ, ни частичная или конфликтующая регистрация не меняют план."""
        plan, draft = self.two_lines()
        assigned = self.assign(plan, draft)
        requested = self.request_order(assigned, draft)
        confirmed = requested.confirm(
            self.supplier_reply(requested), expected_version=1, confirmed_at=self.at
        )
        snapshot = self.inventory_confirmation(confirmed)
        first, second = snapshot.lines
        for changes in (
            dict(order_id=FulfillmentSupplierOrderIdVO(uuid4())),
            dict(
                supplier=FulfillmentSupplierReferenceVO.from_value(
                    "crm.company", uuid4()
                )
            ),
            dict(plan_id=FulfillmentPlanIdVO(uuid4())),
            dict(source_plan_version=snapshot.source_plan_version + 1),
            dict(lines=(first,)),
            dict(lines=(first, second, second)),
            dict(
                lines=(
                    replace(first, line_id=second.line_id),
                    replace(second, line_id=first.line_id),
                )
            ),
            dict(
                lines=(
                    replace(
                        first,
                        allocation=replace(
                            first.allocation, quantity=QuantityVO(Decimal(2))
                        ),
                    ),
                    second,
                )
            ),
            dict(
                lines=(
                    replace(
                        first,
                        allocation=replace(
                            first.allocation,
                            quoted_purchase_price=MoneyVO(
                                Decimal(1), CurrencyVO("USD")
                            ),
                        ),
                    ),
                    second,
                )
            ),
            dict(
                lines=(
                    replace(
                        first,
                        allocation=replace(
                            first.allocation,
                            source=replace(
                                first.allocation.source,
                                supplier_offer_id=FulfillmentSupplierOfferIdVO(uuid4()),
                            ),
                        ),
                    ),
                    second,
                )
            ),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(FulfillmentSupplierOrderConfirmationError),
            ):
                self.register_confirmation(assigned, replace(snapshot, **changes))
        registered = self.register_confirmation(assigned, snapshot)
        changed = replace(
            snapshot,
            confirmation=replace(
                snapshot.confirmation, confirmed_at=self.at + timedelta(seconds=1)
            ),
        )
        with self.assertRaises(FulfillmentSupplierOrderConfirmationError):
            self.register_confirmation(registered, changed)
        self.assertTrue(
            all(row.supplier_confirmation is None for row in assigned.allocations)
        )

    def test_confirmation_versions_status_and_chronology(self) -> None:
        """Требуются запрос, его версия и последовательные моменты ответа и регистрации."""
        assigned = self.assign()
        requested = self.request_order(assigned)
        reply = self.supplier_reply(requested)
        with self.assertRaises(SupplierFulfillmentStatusError):
            self.order.confirm(reply, expected_version=0, confirmed_at=self.at)
        with self.assertRaises(SupplierFulfillmentStatusError):
            requested.confirmation_snapshot()
        with self.assertRaises(SupplierFulfillmentVersionConflictError):
            requested.confirm(reply, expected_version=0, confirmed_at=self.at)
        earlier = self.at - timedelta(seconds=1)
        with self.assertRaises(SupplierFulfillmentTimeError):
            requested.confirm(reply, expected_version=1, confirmed_at=earlier)
        confirmed = requested.confirm(
            reply, expected_version=1, confirmed_at=self.at + timedelta(seconds=1)
        )
        snapshot = self.inventory_confirmation(confirmed)
        with self.assertRaises(FulfillmentPlanVersionConflictError):
            assigned.register_supplier_confirmation(
                snapshot, expected_version=assigned.version - 1, updated_at=self.at
            )
        with self.assertRaises(FulfillmentPlanTimeError):
            assigned.register_supplier_confirmation(
                snapshot, expected_version=assigned.version, updated_at=self.at
            )
        with self.assertRaises(FulfillmentPlanTimeError):
            self.register_confirmation(
                assigned,
                replace(
                    snapshot,
                    confirmation=replace(snapshot.confirmation, requested_at=earlier),
                ),
            )

    def test_partial_reply_frees_only_unconfirmed_demand_before_and_after_shipment(
        self,
    ) -> None:
        """После ответа 2 из 4 свободно 2 PCS независимо от исполнения складской части."""
        assigned = self.assign(self.f.f.confirm_warehouse(self.plan))
        requested = self.request_order(assigned)
        (full_line,) = self.supplier_reply(requested)
        partial_line = replace(
            full_line, quantity=SupplierFulfillmentQuantityVO(Decimal(2))
        )
        confirmed = requested.confirm(
            (partial_line,), expected_version=1, confirmed_at=self.at
        )
        self.assertIs(
            confirmed.status, SupplierFulfillmentOrderStatus.PARTIALLY_CONFIRMED
        )
        self.assertEqual(confirmed.version, 2)
        self.assertEqual(confirmed.lines[0].requested_quantity.value, Decimal(4))
        self.assertEqual(confirmed.lines[0].confirmed_quantity.value, Decimal(2))
        self.assertEqual(self.f.restore(confirmed), confirmed)
        snapshot = self.inventory_confirmation(confirmed)
        before = self.register_confirmation(assigned, snapshot)
        row = before.get_allocation(self.f.allocation_id)
        self.assertEqual(row.quantity, QuantityVO(Decimal(4)))
        self.assertEqual(row.remaining_to_fulfill(), QuantityVO(Decimal(2)))
        self.assertEqual(row.fulfilled_qty, QuantityVO(Decimal(0)))
        self.assertEqual(
            row.supplier_order_assignment,
            assigned.get_allocation(row.id).supplier_order_assignment,
        )
        self.assertIs(before.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertTrue(before.is_fully_confirmed())
        demand = self.f.f.f.demand
        line_ref = self.f.f.f.line_ref
        self.assertEqual(
            before.remaining_to_allocate(line_ref, demand=demand),
            QuantityVO(Decimal(2)),
        )

        draft = self.f.f.shipments.create(
            fulfillment_plan=assigned.shipment_snapshot(),
            created_at=assigned.updated_at,
        )
        with_shipment, ready = self.f.f.shipments.assign_and_confirm(assigned, draft)
        progress = progress_fixture.FulfillmentProgressDomainTests()
        progress.setUp()
        shipped = progress.execute(
            ready, {ready.lines[0].id: "3"}, at=self.at + timedelta(minutes=1)
        )
        after_warehouse = progress.register(with_shipment, shipped)
        after = self.register_confirmation(after_warehouse, snapshot)
        demand_after = replace(
            demand,
            lines=(
                replace(demand.lines[0], remaining_qty=QuantityVO(Decimal(4))),
                *demand.lines[1:],
            ),
        )
        self.assertIs(after.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertTrue(after.is_fully_confirmed())
        self.assertEqual(after.allocations[0], after_warehouse.allocations[0])
        self.assertEqual(after.get_allocation(row.id), row)
        self.assertEqual(
            after.remaining_to_allocate(line_ref, demand=demand_after),
            QuantityVO(Decimal(2)),
        )
        after.shipment_snapshot().ensure_valid()
        self.assertEqual(progress.restore(after), after)

    def test_zero_line_remains_in_history_and_releases_its_whole_quantity(self) -> None:
        """Нулевой ответ отменяет строку, сохраняя принадлежность к ответу всей группы."""
        plan, draft = self.two_lines()
        assigned = self.assign(plan, draft)
        requested = self.request_order(assigned, draft)
        first, second = self.supplier_reply(requested)
        zero = replace(
            second, quantity=SupplierFulfillmentQuantityVO(Decimal(0)), price=None
        )
        confirmed = requested.confirm(
            (first, zero), expected_version=1, confirmed_at=self.at
        )
        self.assertIs(
            confirmed.status, SupplierFulfillmentOrderStatus.PARTIALLY_CONFIRMED
        )
        self.assertIsNone(confirmed.lines[1].confirmed_price)
        self.assertEqual(confirmed.lines[1].confirmed_quantity.value, Decimal(0))
        snapshot = self.inventory_confirmation(confirmed)
        registered = self.register_confirmation(assigned, snapshot)
        historical = registered.allocations[-1]
        self.assertIs(historical.status, FulfillmentAllocationStatus.CANCELLED)
        self.assertEqual(historical.quantity, QuantityVO(Decimal(4)))
        self.assertEqual(historical.remaining_to_fulfill(), QuantityVO(Decimal(0)))
        self.assertEqual(historical.cancelled_at, self.at)
        self.assertEqual(historical.supplier_confirmation, snapshot.confirmation)
        self.assertEqual(
            historical.supplier_order_assignment,
            assigned.allocations[-1].supplier_order_assignment,
        )
        demand = self.f.f.f.demand
        line_ref = self.f.f.f.other_ref
        self.assertEqual(
            registered.remaining_to_allocate(line_ref, demand=demand).value
            - assigned.remaining_to_allocate(line_ref, demand=demand).value,
            Decimal(4),
        )
        self.assertIs(self.register_confirmation(registered, snapshot), registered)
        self.assertIs(
            confirmed.confirm((zero, first), expected_version=2, confirmed_at=self.at),
            confirmed,
        )
        registered.shipment_snapshot().ensure_valid()
        progress = progress_fixture.FulfillmentProgressDomainTests()
        self.assertEqual(progress.restore(registered), registered)

    def test_partial_reply_uses_frozen_step_minimum_and_multiple(self) -> None:
        """Ответ и регистрация проверяют исторические правила независимо от нового предложения."""
        assigned = self.assign()
        new_option = replace(self.f.f.option, order_multiple=QuantityVO(Decimal(4)))
        self.assertIs(self.assign(assigned, supplier_options=(new_option,)), assigned)
        requested = self.request_order(assigned)
        (line,) = self.supplier_reply(requested)
        partial = replace(line, quantity=SupplierFulfillmentQuantityVO(Decimal(2)))
        confirmed = requested.confirm(
            (partial,), expected_version=1, confirmed_at=self.at
        )
        snapshot = self.inventory_confirmation(confirmed)
        ((line_id, _),) = snapshot.confirmed_quantities
        for value in ("1", "3"):
            with self.subTest(value=value):
                invalid = replace(
                    line, quantity=SupplierFulfillmentQuantityVO(Decimal(value))
                )
                with self.assertRaises(SupplierFulfillmentBasisMismatchError):
                    requested.confirm(
                        (invalid,), expected_version=1, confirmed_at=self.at
                    )
                with self.assertRaises(FulfillmentSupplierOrderConfirmationError):
                    self.register_confirmation(
                        assigned,
                        replace(
                            snapshot,
                            confirmed_quantities=(
                                (line_id, QuantityVO(Decimal(value))),
                            ),
                        ),
                    )

        fractional_option = replace(
            self.f.f.option, order_multiple=QuantityVO(Decimal("0.5"))
        )
        fractional = self.assign(supplier_options=(fractional_option,))
        fractional_request = self.request_order(fractional)
        bad_step = replace(line, quantity=SupplierFulfillmentQuantityVO(Decimal("2.5")))
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            fractional_request.confirm(
                (bad_step,), expected_version=1, confirmed_at=self.at
            )
        with self.assertRaises(FulfillmentSupplierOrderConfirmationError):
            self.register_confirmation(
                fractional,
                replace(
                    snapshot,
                    confirmed_quantities=((line_id, QuantityVO(Decimal("2.5"))),),
                ),
            )

    def test_conflicting_replay_and_invalid_partial_state_are_rejected(self) -> None:
        """Зарегистрированное количество неизменно, статус восстановления соответствует ответу."""
        assigned = self.assign()
        requested = self.request_order(assigned)
        (full,) = self.supplier_reply(requested)
        partial = replace(full, quantity=SupplierFulfillmentQuantityVO(Decimal(2)))
        confirmed = requested.confirm(
            (partial,), expected_version=1, confirmed_at=self.at
        )
        snapshot = self.inventory_confirmation(confirmed)
        registered = self.register_confirmation(assigned, snapshot)
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            confirmed.confirm((full,), expected_version=2, confirmed_at=self.at)
        with self.assertRaises(FulfillmentSupplierOrderConfirmationError):
            self.register_confirmation(
                registered,
                replace(
                    snapshot,
                    confirmed_quantities=(
                        (snapshot.lines[0].line_id, QuantityVO(Decimal(4))),
                    ),
                ),
            )
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            self.f.restore(confirmed, status=SupplierFulfillmentOrderStatus.CONFIRMED)
        progress = progress_fixture.FulfillmentProgressDomainTests()
        row = registered.allocations[-1]
        with self.assertRaises(FulfillmentSupplierOrderConfirmationError):
            progress.restore(
                registered,
                allocations=(
                    *registered.allocations[:-1],
                    replace(row, supplier_confirmed_qty=QuantityVO(Decimal(3))),
                ),
            )

    def test_rejects_all_zero_and_incomplete_quantity_evidence(self) -> None:
        """Один отказ по всему запросу и неполный снимок требуют отдельного сценария."""
        assigned = self.assign()
        requested = self.request_order(assigned)
        (full,) = self.supplier_reply(requested)
        zero = SupplierFulfillmentLineConfirmationVO(
            full.line_id, SupplierFulfillmentQuantityVO(Decimal(0)), None
        )
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            requested.confirm((zero,), expected_version=1, confirmed_at=self.at)
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            replace(zero, price=full.price)
        confirmed = requested.confirm((full,), expected_version=1, confirmed_at=self.at)
        snapshot = self.inventory_confirmation(confirmed)
        (entry,) = snapshot.confirmed_quantities
        for quantities in (
            None,
            (),
            (entry, entry),
            ((entry[0], QuantityVO(Decimal(0))),),
        ):
            with (
                self.subTest(quantities=quantities),
                self.assertRaises(FulfillmentSupplierOrderConfirmationError),
            ):
                self.register_confirmation(
                    assigned, replace(snapshot, confirmed_quantities=quantities)
                )

    def test_legacy_request_and_full_confirmation_restore_without_terms(self) -> None:
        """Сохранённый запрос без правил принимает прежний полный ответ."""
        assigned = self.assign()
        row = assigned.allocations[-1]
        progress = progress_fixture.FulfillmentProgressDomainTests()
        legacy = progress.restore(
            assigned,
            allocations=(
                *assigned.allocations[:-1],
                replace(
                    row,
                    supplier_order_assignment=replace(
                        row.supplier_order_assignment, quantity_terms=None
                    ),
                ),
            ),
        )
        requested = self.request_order(legacy)
        self.assertIsNone(requested.lines[0].quantity_terms)
        (full,) = self.supplier_reply(requested)
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            requested.confirm(
                (replace(full, quantity=SupplierFulfillmentQuantityVO(Decimal(2))),),
                expected_version=1,
                confirmed_at=self.at,
            )
        confirmed = requested.confirm((full,), expected_version=1, confirmed_at=self.at)
        snapshot = replace(
            self.inventory_confirmation(confirmed), confirmed_quantities=None
        )
        registered = self.register_confirmation(legacy, snapshot)
        legacy_confirmed = progress.restore(
            registered,
            allocations=(
                *registered.allocations[:-1],
                replace(registered.allocations[-1], supplier_confirmed_qty=None),
            ),
        )
        self.assertEqual(
            legacy_confirmed.allocations[-1].remaining_to_fulfill(),
            QuantityVO(Decimal(4)),
        )
        self.assertIs(
            self.register_confirmation(legacy_confirmed, snapshot), legacy_confirmed
        )

    def inventory_rejection(
        self, order: SupplierFulfillmentOrder
    ) -> SupplierOrderRejectionSnapshot:
        """Передаёт отказ с исходными строками в номинальных типах Inventory."""
        snapshot = order.rejection_snapshot()
        return SupplierOrderRejectionSnapshot(
            order_id=FulfillmentSupplierOrderIdVO(snapshot.order_id.uuid),
            supplier=FulfillmentSupplierReferenceVO.from_value(
                snapshot.supplier.model_key.value, snapshot.supplier.identifier.uuid
            ),
            plan_id=FulfillmentPlanIdVO(snapshot.plan_ref.plan_id.uuid),
            source_plan_version=snapshot.plan_ref.plan_version,
            rejection=FulfillmentSupplierOrderRejectionRefVO(
                snapshot.order_version, snapshot.requested_at, snapshot.rejected_at
            ),
            lines=self.inventory_lines(snapshot.allocations, snapshot.line_bindings),
        )

    def register_rejection(
        self, plan: FulfillmentPlan, snapshot: SupplierOrderRejectionSnapshot
    ) -> FulfillmentPlan:
        """Регистрирует явный отказ по текущей версии плана."""
        return plan.register_supplier_rejection(
            snapshot,
            expected_version=plan.version,
            updated_at=max(plan.updated_at, snapshot.rejection.rejected_at),
        )

    def test_rejection_preserves_request_and_frees_all_supplier_demand(self) -> None:
        """Отказ сохраняет историю внешней строки и действующее складское подтверждение."""
        assigned = self.assign(self.f.f.confirm_warehouse(self.plan))
        requested = self.request_order(assigned)
        reason = "Нет товара"
        rejected = requested.reject(
            expected_version=1,
            rejected_at=self.at.astimezone(timezone(timedelta(hours=2))),
            reason=reason,
        )
        self.assertIs(rejected.status, SupplierFulfillmentOrderStatus.REJECTED)
        self.assertEqual(rejected.version, 2)
        self.assertEqual(rejected.rejected_at, self.at)
        self.assertIs(rejected.rejected_at.tzinfo, UTC)
        self.assertEqual(rejected.rejection_reason, reason)
        self.assertEqual(rejected.lines, requested.lines)
        self.assertIsNone(rejected.confirmed_at)
        self.assertEqual(self.f.restore(rejected), rejected)
        self.assertIs(
            rejected.reject(expected_version=2, rejected_at=self.at, reason=reason),
            rejected,
        )
        evidence = self.inventory_rejection(rejected)
        result = self.register_rejection(assigned, evidence)
        self.assertIs(result.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertEqual(result.version, assigned.version + 1)
        self.assertEqual(result.allocations[0], assigned.allocations[0])
        row = result.get_allocation(self.f.allocation_id)
        self.assertIs(row.status, FulfillmentAllocationStatus.CANCELLED)
        self.assertEqual(row.quantity, QuantityVO(Decimal(4)))
        self.assertEqual(row.cancelled_at, self.at)
        self.assertEqual(row.remaining_to_fulfill(), QuantityVO(Decimal(0)))
        self.assertEqual(row.supplier_rejection, evidence.rejection)
        self.assertIsNone(row.supplier_confirmation)
        self.assertEqual(
            row.supplier_order_assignment,
            assigned.get_allocation(row.id).supplier_order_assignment,
        )
        fixture = self.f.f.f
        self.assertEqual(
            result.remaining_to_allocate(fixture.line_ref, demand=fixture.demand),
            QuantityVO(Decimal(4)),
        )
        result.shipment_snapshot().ensure_valid()
        self.assertIs(self.register_rejection(result, evidence), result)

    def test_only_supplier_rejection_waits_for_new_allocation(self) -> None:
        """План с одной отклонённой строкой остаётся доступным для допланирования."""
        warehouse, external = self.plan.allocations
        plan = self.plan.cancel_allocations(
            allocation_ids=(warehouse.id,),
            expected_version=self.plan.version,
            updated_at=self.plan.updated_at,
        )
        basis = self.f.map_basis(plan, external.id)
        draft = self.f.create(basis=basis, line_bindings=self.f.bindings(basis))
        assigned = self.assign(plan, draft)
        requested = self.request_order(assigned, draft)
        rejected = requested.reject(expected_version=1, rejected_at=self.at)
        evidence = self.inventory_rejection(rejected)
        waiting = self.register_rejection(assigned, evidence)
        self.assertIs(waiting.status, FulfillmentPlanStatus.AWAITING_ALLOCATION)
        self.assertFalse(waiting.is_fully_confirmed())
        fixture = self.f.f.f
        self.assertEqual(
            waiting.remaining_to_allocate(fixture.line_ref, demand=fixture.demand),
            QuantityVO(Decimal(7)),
        )
        progress = progress_fixture.FulfillmentProgressDomainTests()
        self.assertEqual(progress.restore(waiting), waiting)

        new = replace(
            warehouse,
            id=FulfillmentAllocationIdVO(uuid4()),
            quantity=QuantityVO(Decimal(7)),
        )
        extended = waiting.allocate_remaining_demand(
            allocations=(new,),
            demand=fixture.demand,
            inventory_items=(fixture.item,),
            warehouses=(fixture.a,),
            expected_version=waiting.version,
            updated_at=self.at,
        )
        self.assertIs(extended.status, FulfillmentPlanStatus.PLANNED)
        self.assertEqual(extended.allocations[:-1], waiting.allocations)
        self.assertEqual(
            extended.remaining_to_allocate(fixture.line_ref, demand=fixture.demand),
            QuantityVO(Decimal(0)),
        )
        self.assertIs(self.register_rejection(extended, evidence), extended)
        cancelled = extended.cancel(
            expected_version=extended.version, updated_at=extended.updated_at
        )
        self.assertIs(self.register_rejection(cancelled, evidence), cancelled)
        with self.assertRaises(FulfillmentPlanStatusError):
            cancelled.remaining_to_allocate(fixture.line_ref, demand=fixture.demand)

    def test_reallocates_remaining_demand_after_warehouse_shipment_in_both_orders(
        self,
    ) -> None:
        """Отказ и складская отгрузка в любом порядке освобождают 4 PCS для нового склада."""
        assigned = self.assign(self.f.f.confirm_warehouse(self.plan))
        requested = self.request_order(assigned)
        evidence = self.inventory_rejection(
            requested.reject(expected_version=1, rejected_at=self.at)
        )
        fixture = self.f.f.f
        demand = replace(
            fixture.demand,
            lines=(
                replace(fixture.demand.lines[0], remaining_qty=QuantityVO(Decimal(4))),
                *fixture.demand.lines[1:],
            ),
        )
        warehouse = self.plan.allocations[0]
        new = replace(
            warehouse,
            id=FulfillmentAllocationIdVO(uuid4()),
            source=replace(warehouse.source, warehouse_id=fixture.b.id),
            quantity=QuantityVO(Decimal(4)),
        )
        progress = progress_fixture.FulfillmentProgressDomainTests()
        progress.setUp()
        for reject_first in (False, True):
            with self.subTest(reject_first=reject_first):
                before = (
                    self.register_rejection(assigned, evidence)
                    if reject_first
                    else assigned
                )
                draft = self.f.f.shipments.create(
                    fulfillment_plan=before.shipment_snapshot(),
                    created_at=before.updated_at,
                )
                with_shipment, ready = self.f.f.shipments.assign_and_confirm(
                    before, draft
                )
                shipped = progress.execute(
                    ready, {ready.lines[0].id: "3"}, at=self.at + timedelta(minutes=1)
                )
                after_shipment = progress.register(with_shipment, shipped)
                if reject_first:
                    freed = after_shipment
                    self.assertIs(freed.status, FulfillmentPlanStatus.FULFILLED)
                else:
                    self.assertIs(
                        after_shipment.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED
                    )
                    freed = self.register_rejection(after_shipment, evidence)
                    self.assertIs(
                        freed.status, FulfillmentPlanStatus.AWAITING_ALLOCATION
                    )
                self.assertEqual(progress.restore(freed), freed)
                self.assertEqual(
                    freed.allocations[0].fulfilled_qty, QuantityVO(Decimal(3))
                )
                self.assertEqual(
                    freed.remaining_to_allocate(fixture.line_ref, demand=demand),
                    QuantityVO(Decimal(4)),
                )
                extended = freed.allocate_remaining_demand(
                    allocations=(new,),
                    demand=demand,
                    inventory_items=(fixture.item,),
                    warehouses=(fixture.b,),
                    expected_version=freed.version,
                    updated_at=freed.updated_at,
                )
                self.assertIs(
                    extended.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED
                )
                self.assertEqual(extended.allocations[:-1], freed.allocations)
                self.assertEqual(
                    extended.remaining_to_allocate(fixture.line_ref, demand=demand),
                    QuantityVO(Decimal(0)),
                )
                self.assertIs(self.register_rejection(extended, evidence), extended)

    def test_rejection_requires_the_entire_original_group(self) -> None:
        """Чужой, неполный или изменённый ответ не закрывает ни одной из строк."""
        plan, draft = self.two_lines()
        assigned = self.assign(plan, draft)
        requested = self.request_order(assigned, draft)
        evidence = self.inventory_rejection(
            requested.reject(expected_version=1, rejected_at=self.at)
        )
        first, second = evidence.lines
        for changes in (
            dict(order_id=FulfillmentSupplierOrderIdVO(uuid4())),
            dict(
                supplier=FulfillmentSupplierReferenceVO.from_value(
                    "crm.company", uuid4()
                )
            ),
            dict(plan_id=FulfillmentPlanIdVO(uuid4())),
            dict(source_plan_version=evidence.source_plan_version + 1),
            dict(lines=(first,)),
            dict(lines=(first, second, second)),
            dict(
                lines=(
                    replace(first, line_id=FulfillmentSupplierOrderLineIdVO(uuid4())),
                    second,
                )
            ),
            dict(
                lines=(
                    replace(
                        first,
                        allocation=replace(
                            first.allocation, quantity=QuantityVO(Decimal(2))
                        ),
                    ),
                    second,
                )
            ),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(FulfillmentSupplierOrderRejectionError),
            ):
                self.register_rejection(assigned, replace(evidence, **changes))
        with self.assertRaises(FulfillmentPlanVersionConflictError):
            assigned.register_supplier_rejection(
                evidence, expected_version=assigned.version - 1, updated_at=self.at
            )
        result = self.register_rejection(assigned, evidence)
        self.assertEqual(result.version, assigned.version + 1)
        self.assertEqual(result.allocations[0], assigned.allocations[0])
        self.assertTrue(
            all(
                row.status is FulfillmentAllocationStatus.CANCELLED
                for row in result.allocations[1:]
            )
        )
        self.assertTrue(
            all(row.supplier_rejection is None for row in assigned.allocations)
        )
        self.assertIs(
            self.register_rejection(result, replace(evidence, lines=(second, first))),
            result,
        )
        changed = replace(
            evidence,
            rejection=replace(
                evidence.rejection, rejected_at=self.at + timedelta(seconds=1)
            ),
        )
        with self.assertRaises(FulfillmentSupplierOrderRejectionError):
            self.register_rejection(result, changed)
        progress = progress_fixture.FulfillmentProgressDomainTests()
        with self.assertRaises(FulfillmentSupplierOrderAssignmentError):
            progress.restore(
                result, allocations=(*result.allocations[:-1], assigned.allocations[-1])
            )

    def test_rejection_is_exclusive_with_confirmation_and_requires_requested_version(
        self,
    ) -> None:
        """Отказ и подтверждение взаимоисключающие, включая частичный ответ."""
        assigned = self.assign()
        requested = self.request_order(assigned)
        earlier = self.at - timedelta(seconds=1)
        with self.assertRaises(SupplierFulfillmentStatusError):
            self.order.reject(expected_version=0, rejected_at=self.at)
        with self.assertRaises(SupplierFulfillmentVersionConflictError):
            requested.reject(expected_version=0, rejected_at=self.at)
        with self.assertRaises(SupplierFulfillmentTimeError):
            requested.reject(expected_version=1, rejected_at=earlier)
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            requested.reject(expected_version=1, rejected_at=self.at, reason=" ")
        with self.assertRaises(SupplierFulfillmentStatusError):
            requested.rejection_snapshot()
        rejected = requested.reject(expected_version=1, rejected_at=self.at)
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            rejected.reject(
                expected_version=2, rejected_at=self.at, reason="Новая причина"
            )
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            self.f.restore(rejected, rejected_at=None)
        with self.assertRaises(SupplierFulfillmentStatusError):
            rejected.confirm(
                self.supplier_reply(requested), expected_version=2, confirmed_at=self.at
            )
        evidence = self.inventory_rejection(rejected)
        registered_rejection = self.register_rejection(assigned, evidence)
        (line,) = self.supplier_reply(requested)
        for quantity in (Decimal(2), Decimal(4)):
            with self.subTest(quantity=quantity):
                confirmed = requested.confirm(
                    (replace(line, quantity=SupplierFulfillmentQuantityVO(quantity)),),
                    expected_version=1,
                    confirmed_at=self.at,
                )
                with self.assertRaises(SupplierFulfillmentStatusError):
                    confirmed.reject(expected_version=2, rejected_at=self.at)
                confirmation = self.inventory_confirmation(confirmed)
                registered_confirmation = self.register_confirmation(
                    assigned, confirmation
                )
                with self.assertRaises(FulfillmentSupplierOrderRejectionError):
                    self.register_rejection(registered_confirmation, evidence)
                with self.assertRaises(FulfillmentSupplierOrderConfirmationError):
                    self.register_confirmation(registered_rejection, confirmation)
