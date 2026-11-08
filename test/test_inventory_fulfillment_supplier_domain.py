"""Ручная прямая поставка и складское исполнение в смешанном плане."""

import unittest
from dataclasses import fields, replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from test import test_inventory_fulfillment_progress_domain as progress_fixture
from test import test_inventory_fulfillment_shipment_domain as shipment_fixture
from test import test_supplier_offer_domain as supplier_fixture
from src.modules.inventory.domain.error import QuantityStepError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentAllocationConflictError,
    FulfillmentAllocationExtensionConflictError,
    FulfillmentDemandExceededError,
    FulfillmentPlanContextError,
    FulfillmentReplanningConflictError,
    FulfillmentReservationMismatchError,
    FulfillmentSourceSplitForbiddenError,
    InvalidFulfillmentAllocationError,
    InvalidFulfillmentSourceError,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_dropship_option_snapshot import (
    SupplierDropshipOptionSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_kind import (
    FulfillmentSourceKind,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_dropship_source_ref import (
    SupplierDropshipSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierIdVO,
    FulfillmentSupplierOfferIdVO,
    FulfillmentSupplierSourceIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidFulfillmentShipmentLineBindingError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.supplier_sourcing.domain.supplier_offer.item_snapshot import (
    SupplierOfferItemSnapshot,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.order_quantity import (
    SupplierOrderQuantityVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.uom_code import (
    SupplierOfferUomCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.value_object.inventory_item_id import (
    SupplierInventoryItemIdVO,
)


class FulfillmentSupplierDomainTests(unittest.TestCase):
    """Проверяет коммерческие инварианты и изоляцию внешних строк от складского исполнения."""

    def setUp(self) -> None:
        """Готовит 3 PCS собственного склада и предложение поставщика на тот же товар."""
        self.shipments = shipment_fixture.FulfillmentShipmentDomainTests()
        self.shipments.setUp()
        self.reservations = self.shipments.f
        self.f = self.reservations.f
        supplier = supplier_fixture.SupplierOfferDomainTests()
        supplier.setUp()
        source = supplier.source(supplier.supplier_id)
        offer = supplier.create(
            item=SupplierOfferItemSnapshot(
                SupplierInventoryItemIdVO(self.f.item.inventory_item_id.uuid),
                SupplierOfferUomCodeVO(self.f.item.base_uom.value),
            ),
            source=source.identity_snapshot(),
            min_order_qty=SupplierOrderQuantityVO(Decimal(2)),
            order_multiple=SupplierOrderQuantityVO(Decimal(2)),
        )
        self.supplier_source, self.supplier_offer = source, offer
        self.option = SupplierDropshipOptionSnapshot(
            source=SupplierDropshipSourceRefVO(
                FulfillmentSupplierSourceIdVO(source.id.uuid),
                FulfillmentSupplierOfferIdVO(offer.id.uuid),
            ),
            source_supplier_id=FulfillmentSupplierIdVO(source.supplier_id.uuid),
            offer_supplier_id=FulfillmentSupplierIdVO(offer.supplier_id.uuid),
            offer_source_id=FulfillmentSupplierSourceIdVO(offer.source_id.uuid),
            source_is_active=source.is_active,
            source_supports_dropship=SupplierFulfillmentMode.DROPSHIP
            in source.fulfillment_modes,
            offer_is_active=offer.is_active,
            inventory_item_id=InventoryItemIdVO(offer.inventory_item_id.uuid),
            base_uom=UomCodeVO(offer.base_uom.value),
            purchase_price=offer.purchase_price,
            min_order_qty=QuantityVO(offer.min_order_qty.value),
            order_multiple=QuantityVO(offer.order_multiple.value),
        )
        self.supplier_allocation_id = FulfillmentAllocationIdVO(uuid4())

    def add(
        self, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Добавляет внешнюю строку с явной версией и актуальным контекстом заказа."""
        target = self.f.one if plan is None else plan
        return target.add_supplier_allocation(
            **(
                dict(
                    identifier=self.supplier_allocation_id,
                    source_ref=self.f.line_ref,
                    quantity=QuantityVO(Decimal(4)),
                    demand=self.f.demand,
                    inventory_item=self.f.item,
                    supplier_option=self.option,
                    expected_version=target.version,
                    updated_at=self.shipments.at,
                )
                | changes
            )
        )

    def mark(self, plan: FulfillmentPlan, **changes: object) -> FulfillmentPlan:
        """Фиксирует план по текущим снимкам обоих типов источников."""
        return plan.mark_planned(
            **(
                dict(
                    demand=self.f.demand,
                    inventory_items=(self.f.item,),
                    warehouses=(self.f.a,),
                    supplier_options=(self.option,),
                    expected_version=plan.version,
                    updated_at=self.shipments.at,
                )
                | changes
            )
        )

    def confirm_warehouse(
        self, plan: FulfillmentPlan, **changes: object
    ) -> FulfillmentPlan:
        """Подтверждает складскую часть смешанного плана существующим резервом."""
        return self.reservations.confirm(
            plan,
            **(
                dict(
                    bindings=(self.reservations.first_binding,),
                    reservations=(self.shipments.reservation,),
                    warehouses=(self.f.a,),
                    updated_at=self.shipments.at,
                )
                | changes
            ),
        )

    def test_adds_and_restores_mixed_plan_with_supplier_price_and_no_reservation(
        self,
    ) -> None:
        """Смешанный план фиксирует 3 + 4 PCS и сохраняет цену внешней строки."""
        draft = self.add()
        planned = self.mark(draft)
        row = planned.get_allocation(self.supplier_allocation_id)
        self.assertEqual(planned.status, FulfillmentPlanStatus.PLANNED)
        self.assertEqual(
            planned.remaining_to_allocate(self.f.line_ref, demand=self.f.demand),
            QuantityVO(Decimal(0)),
        )
        self.assertEqual(row.source.kind, FulfillmentSourceKind.SUPPLIER_DROPSHIP)
        self.assertEqual(row.source, self.option.source)
        self.assertEqual(row.quoted_purchase_price, self.option.purchase_price)
        self.assertEqual(row.status, FulfillmentAllocationStatus.PLANNED)
        self.assertIsNone(row.reservation)
        self.assertEqual(self.f.one.allocations, (self.f.allocation,))
        values = {field.name: getattr(planned, field.name) for field in fields(planned)}
        values["identifier"] = values.pop("id")
        self.assertEqual(FulfillmentPlan.restore(**values), planned)

    def test_rejects_wrong_supplier_source_product_unit_and_inactive_or_wrong_mode(
        self,
    ) -> None:
        """Типизированный снимок должен соответствовать активной прямой поставке этого товара."""
        for changes in (
            dict(offer_supplier_id=FulfillmentSupplierIdVO(uuid4())),
            dict(offer_source_id=FulfillmentSupplierSourceIdVO(uuid4())),
            dict(source_is_active=False),
            dict(offer_is_active=False),
            dict(source_supports_dropship=False),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("KG")),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(FulfillmentPlanContextError),
            ):
                self.add(supplier_option=replace(self.option, **changes))
        with self.assertRaises(InvalidFulfillmentSourceError):
            SupplierDropshipSourceRefVO(
                self.option.source.supplier_offer_id,
                self.option.source.supplier_source_id,
            )

    def test_checks_minimum_multiple_and_inventory_step_independently(self) -> None:
        """Коммерческая кратность не заменяет минимальный заказ и складской шаг."""
        for quantity in (1, 3):
            with (
                self.subTest(quantity=quantity),
                self.assertRaises(InvalidFulfillmentAllocationError),
            ):
                self.add(quantity=QuantityVO(Decimal(quantity)))
        with self.assertRaises(QuantityStepError):
            self.add(
                inventory_item=replace(
                    self.f.item, quantity_rules=QuantityRulesVO(Decimal(3))
                )
            )

    def test_rejects_demand_overflow_forbidden_split_and_duplicate_option(self) -> None:
        """Собственные и внешние строки делят один лимит потребности."""
        with self.assertRaises(FulfillmentDemandExceededError):
            self.add(quantity=QuantityVO(Decimal(6)))
        unsplittable = replace(
            self.f.demand,
            lines=(
                replace(self.f.first_demand, allow_source_split=False),
                self.f.other_demand,
            ),
        )
        with self.assertRaises(FulfillmentSourceSplitForbiddenError):
            self.add(demand=unsplittable)
        with self.assertRaises(FulfillmentAllocationConflictError):
            self.add(
                self.add(quantity=QuantityVO(Decimal(2))),
                identifier=FulfillmentAllocationIdVO(uuid4()),
                quantity=QuantityVO(Decimal(2)),
            )

    def test_changes_quantity_with_current_terms_and_requires_explicit_reselection_on_price_change(
        self,
    ) -> None:
        """Правка количества проверяет предложение, а новая цена фиксируется через явный выбор."""
        draft = self.add(quantity=QuantityVO(Decimal(2)))
        args = dict(
            identifier=self.supplier_allocation_id,
            quantity=QuantityVO(Decimal(4)),
            demand=self.f.demand,
            inventory_item=self.f.item,
            supplier_option=self.option,
            expected_version=draft.version,
            updated_at=self.shipments.at,
        )
        changed = draft.change_supplier_allocation_quantity(**args)
        self.assertEqual(
            changed.get_allocation(self.supplier_allocation_id).quantity,
            QuantityVO(Decimal(4)),
        )
        self.assertEqual(
            draft.get_allocation(self.supplier_allocation_id).quantity,
            QuantityVO(Decimal(2)),
        )
        new_option = replace(
            self.option, purchase_price=MoneyVO(Decimal(101), CurrencyVO("UAH"))
        )
        with self.assertRaises(FulfillmentPlanContextError):
            draft.change_supplier_allocation_quantity(
                **(args | dict(supplier_option=new_option))
            )
        with self.assertRaises(FulfillmentPlanContextError):
            self.mark(changed, supplier_options=(new_option,))
        without_supplier = changed.remove_allocation(
            self.supplier_allocation_id,
            expected_version=changed.version,
            updated_at=self.shipments.at,
        )
        selected = self.add(without_supplier, supplier_option=new_option)
        planned = self.mark(selected, supplier_options=(new_option,))
        self.assertEqual(
            planned.get_allocation(self.supplier_allocation_id).quoted_purchase_price,
            new_option.purchase_price,
        )

    def test_mark_requires_exact_current_supplier_options_and_supports_supplier_only(
        self,
    ) -> None:
        """Внешний план фиксируется без складов и требует свежие условия всех своих строк."""
        draft = self.add(self.f.draft)
        for options in (
            (),
            (self.option, self.option),
            (replace(self.option, offer_is_active=False),),
        ):
            with (
                self.subTest(options=options),
                self.assertRaises(FulfillmentPlanContextError),
            ):
                self.mark(draft, warehouses=(), supplier_options=options)
        self.assertEqual(
            self.mark(draft, warehouses=()).status, FulfillmentPlanStatus.PLANNED
        )

    def test_warehouse_reservation_and_shipment_leave_supplier_allocation_planned(
        self,
    ) -> None:
        """Складская часть проходит подтверждение и отгрузку, внешняя остаётся намерением."""
        planned = self.mark(self.add())
        confirmed = self.confirm_warehouse(planned)
        self.assertEqual(confirmed.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertEqual(
            confirmed.get_allocation(self.supplier_allocation_id),
            planned.get_allocation(self.supplier_allocation_id),
        )
        draft = self.shipments.create(fulfillment_plan=confirmed.shipment_snapshot())
        self.assertEqual(
            [line.fulfillment_allocation_id for line in draft.lines],
            [self.f.allocation.id],
        )
        assigned, shipment = self.shipments.assign_and_confirm(confirmed, draft)
        progress = progress_fixture.FulfillmentProgressDomainTests()
        progress.setUp()
        shipped = progress.execute(
            shipment,
            {shipment.lines[0].id: "3"},
            at=self.shipments.at + timedelta(minutes=1),
        )
        updated = progress.register(assigned, shipped)
        self.assertEqual(updated.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertEqual(
            updated.get_allocation(self.f.allocation.id).status,
            FulfillmentAllocationStatus.FULFILLED,
        )
        self.assertEqual(
            updated.get_allocation(self.supplier_allocation_id),
            planned.get_allocation(self.supplier_allocation_id),
        )

    def test_explicit_warehouse_bindings_cannot_select_supplier_allocation(
        self,
    ) -> None:
        """Попытки назначить резерв или Shipment внешней строке дают доменные ошибки."""
        planned = self.mark(self.add())
        with self.assertRaises(FulfillmentReservationMismatchError):
            self.confirm_warehouse(
                planned,
                bindings=(
                    replace(
                        self.reservations.first_binding,
                        allocation_id=self.supplier_allocation_id,
                    ),
                ),
            )
        confirmed = self.confirm_warehouse(planned)
        with self.assertRaises(InvalidFulfillmentShipmentLineBindingError):
            self.shipments.create(
                fulfillment_plan=confirmed.shipment_snapshot(),
                line_bindings=(
                    replace(
                        self.shipments.binding,
                        allocation_id=self.supplier_allocation_id,
                    ),
                ),
            )
        supplier_row = planned.get_allocation(self.supplier_allocation_id)
        with self.assertRaises(InvalidFulfillmentAllocationError):
            replace(supplier_row, quoted_purchase_price=None).ensure_valid()

    def test_warehouse_extension_and_replanning_cannot_bypass_supplier_validation(
        self,
    ) -> None:
        """Складские переходы принимают новые строки только своего типа."""
        supplier_row = self.add().get_allocation(self.supplier_allocation_id)
        planned = self.f.mark()
        context = dict(
            demand=self.f.demand,
            inventory_items=(self.f.item,),
            warehouses=(self.f.a,),
            expected_version=planned.version,
            updated_at=self.shipments.at,
        )
        with self.assertRaises(FulfillmentAllocationExtensionConflictError):
            planned.allocate_remaining_demand(allocations=(supplier_row,), **context)
        with self.assertRaises(FulfillmentReplanningConflictError):
            planned.replan_allocations(
                allocation_ids=(self.f.allocation.id,),
                replacements=(supplier_row,),
                **context,
            )
