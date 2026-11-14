from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from src.modules.external_fulfillment.domain.value_object.supplier_reference import (
    ExternalSupplierReferenceVO,
)

"""Черновик прямой поставки на основании выбранных распределений FulfillmentPlan."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from test import test_inventory_fulfillment_progress_domain as progress_fixture
from test import test_inventory_fulfillment_supplier_domain as supplier_fixture
from src.modules.external_fulfillment.domain.aggregate import SupplierFulfillmentOrder
from src.modules.external_fulfillment.domain.draft_basis_snapshot import (
    SupplierFulfillmentAllocationSnapshot,
    SupplierFulfillmentOfferSnapshot,
    SupplierFulfillmentPlanBasisSnapshot,
    SupplierFulfillmentSourceSnapshot,
)
from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
    SupplierFulfillmentBasisMismatchError,
    SupplierFulfillmentTimeError,
)
from src.modules.external_fulfillment.domain.value_object.delivery_address import (
    SupplierDeliveryAddressVO,
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
from src.modules.external_fulfillment.domain.value_object.quantity import (
    SupplierFulfillmentQuantityVO,
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
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentAllocationNotFoundError,
    FulfillmentPlanContextError,
    FulfillmentPlanStatusError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierOfferIdVO,
    FulfillmentSupplierSourceIdVO,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.supplier_sourcing.domain.supplier_offer.aggregate import SupplierOffer
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)


class SupplierFulfillmentOrderDomainTests(unittest.TestCase):
    """Проверяет экспорт плана, формирование черновика и защиту его основания."""

    def setUp(self) -> None:
        """Готовит смешанный план 3 + 4 PCS и авторитетные данные поставщика."""
        self.f = supplier_fixture.FulfillmentSupplierDomainTests()
        self.f.setUp()
        self.draft = self.f.add()
        self.planned = self.f.mark(self.draft)
        self.allocation_id = self.f.supplier_allocation_id
        self.basis = self.map_basis(self.planned, self.allocation_id)
        source = self.f.supplier_source
        self.source = SupplierFulfillmentSourceSnapshot(
            ExternalSupplierSourceIdVO(source.id.uuid),
            ExternalSupplierReferenceVO.from_value(
                source.supplier.model_key.value, source.supplier.identifier.uuid
            ),
            source.is_active,
            SupplierFulfillmentMode.DROPSHIP in source.fulfillment_modes,
        )
        self.offer = self.map_offer(self.f.supplier_offer)
        self.address = SupplierDeliveryAddressVO(
            " ua ", " Київ ", " вул. Тестова, 1 ", " 01001 "
        )

    def map_basis(
        self, plan: FulfillmentPlan, *allocation_ids: FulfillmentAllocationIdVO
    ) -> SupplierFulfillmentPlanBasisSnapshot:
        """Переводит выбранные данные плана в номинальные типы принимающего контекста."""
        source = plan.supplier_order_basis_snapshot(allocation_ids=allocation_ids)
        return SupplierFulfillmentPlanBasisSnapshot(
            plan_ref=SupplierFulfillmentPlanRefVO(
                ExternalFulfillmentPlanIdVO(source.plan_id.uuid), source.plan_version
            ),
            plan_updated_at=source.plan_updated_at,
            allocations=tuple(
                SupplierFulfillmentAllocationSnapshot(
                    allocation_id=ExternalFulfillmentAllocationIdVO(row.id.uuid),
                    inventory_item_id=ExternalInventoryItemIdVO(
                        row.inventory_item_id.uuid
                    ),
                    supplier_source_id=ExternalSupplierSourceIdVO(
                        row.source.supplier_source_id.uuid
                    ),
                    supplier_offer_id=ExternalSupplierOfferIdVO(
                        row.source.supplier_offer_id.uuid
                    ),
                    base_uom=SupplierFulfillmentUomCodeVO(row.base_uom.value),
                    quantity=SupplierFulfillmentQuantityVO(row.quantity.value),
                    quoted_price=row.quoted_purchase_price,
                )
                for row in source.allocations
            ),
        )

    def map_offer(self, offer: SupplierOffer) -> SupplierFulfillmentOfferSnapshot:
        """Передаёт текущую идентичность предложения, сохраняя цену в основании плана."""
        return SupplierFulfillmentOfferSnapshot(
            id=ExternalSupplierOfferIdVO(offer.id.uuid),
            supplier=ExternalSupplierReferenceVO.from_value(
                offer.supplier.model_key.value, offer.supplier.identifier.uuid
            ),
            source_id=(
                ExternalSupplierSourceIdVO(offer.source_id.uuid)
                if offer.source_id
                else None
            ),
            inventory_item_id=ExternalInventoryItemIdVO(offer.inventory_item_id.uuid),
            base_uom=SupplierFulfillmentUomCodeVO(offer.base_uom.value),
            is_active=offer.is_active,
        )

    def bindings(
        self, basis: SupplierFulfillmentPlanBasisSnapshot
    ) -> tuple[SupplierFulfillmentLineBindingVO, ...]:
        """Назначает внешний ID строки каждому явно выбранному распределению."""
        return tuple(
            SupplierFulfillmentLineBindingVO(
                row.allocation_id, SupplierFulfillmentLineIdVO(uuid4())
            )
            for row in basis.allocations
        )

    def create(self, **changes: object) -> SupplierFulfillmentOrder:
        """Создаёт черновик из специализированных снимков без передачи чужих агрегатов."""
        return SupplierFulfillmentOrder.create_from_plan(
            **(
                dict(
                    identifier=SupplierFulfillmentOrderIdVO(uuid4()),
                    basis=self.basis,
                    source=self.source,
                    offers=(self.offer,),
                    line_bindings=self.bindings(self.basis),
                    delivery_address=self.address,
                    created_at=self.basis.plan_updated_at,
                )
                | changes
            )
        )

    def restore(
        self, order: SupplierFulfillmentOrder, **changes: object
    ) -> SupplierFulfillmentOrder:
        """Восстанавливает весь сохранённый состав без исходного плана."""
        values = {field.name: getattr(order, field.name) for field in fields(order)}
        values["identifier"] = values.pop("id")
        return SupplierFulfillmentOrder.restore(**(values | changes))

    def test_creates_only_selected_external_line_and_preserves_historical_quote(
        self,
    ) -> None:
        """Из смешанного плана в черновик попадают 4 PCS и цена, согласованная в плане."""
        later_price = MoneyVO(Decimal(300), CurrencyVO("USD"))
        current_offer = self.f.supplier_offer.change_purchase_price(later_price)
        order = self.create(offers=(self.map_offer(current_offer),))
        self.assertIs(order.status, SupplierFulfillmentOrderStatus.DRAFT)
        self.assertEqual(order.version, 0)
        self.assertEqual(order.plan_ref, self.basis.plan_ref)
        self.assertEqual(order.supplier, self.source.supplier)
        self.assertEqual(order.supplier_source_id, self.source.id)
        self.assertEqual(order.delivery_address, self.address)
        self.assertEqual(len(order.lines), 1)
        line = order.lines[0]
        self.assertEqual(line.fulfillment_allocation_id.uuid, self.allocation_id.uuid)
        self.assertEqual(
            line.inventory_item_id.uuid, self.f.f.item.inventory_item_id.uuid
        )
        self.assertEqual(line.supplier_offer_id, self.offer.id)
        self.assertEqual(line.base_uom.value, "PCS")
        self.assertEqual(line.requested_quantity.value, Decimal(4))
        self.assertEqual(line.quoted_price, self.f.option.purchase_price)
        self.assertNotEqual(line.quoted_price, later_price)
        self.assertEqual(self.restore(order), order)

    def test_accepts_two_lines_for_same_item_and_offer_without_merging(self) -> None:
        """Каждая строка сохраняет свой allocation_id даже для одного SKU и предложения."""
        another = FulfillmentAllocationIdVO(uuid4())
        draft = self.f.add(
            self.draft, identifier=another, source_ref=self.f.f.other_ref
        )
        planned = self.f.mark(draft)
        basis = self.map_basis(planned, another, self.allocation_id)
        bindings = self.bindings(basis)
        order = self.create(basis=basis, line_bindings=bindings[::-1])
        self.assertEqual(
            [line.id for line in order.lines], [binding.line_id for binding in bindings]
        )
        self.assertEqual(
            [line.fulfillment_allocation_id.uuid for line in order.lines],
            [another.uuid, self.allocation_id.uuid],
        )
        self.assertEqual(
            [line.requested_quantity.value for line in order.lines],
            [Decimal(4), Decimal(4)],
        )

    def test_creates_draft_after_warehouse_shipment_of_mixed_plan(self) -> None:
        """Исполнение складских 3 PCS оставляет внешнее распределение доступным для черновика."""
        confirmed = self.f.confirm_warehouse(self.planned)
        shipment = self.f.shipments.create(
            fulfillment_plan=confirmed.shipment_snapshot()
        )
        assigned, shipment = self.f.shipments.assign_and_confirm(confirmed, shipment)
        progress = progress_fixture.FulfillmentProgressDomainTests()
        progress.setUp()
        shipped = progress.execute(
            shipment,
            {shipment.lines[0].id: "3"},
            at=self.f.shipments.at + timedelta(minutes=1),
        )
        after = progress.register(assigned, shipped)
        self.assertIs(after.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        basis = self.map_basis(after, self.allocation_id)
        order = self.create(basis=basis, created_at=basis.plan_updated_at)
        self.assertEqual(order.plan_ref.plan_version, after.version)
        self.assertEqual(order.lines[0].requested_quantity.value, Decimal(4))
        self.assertEqual(
            after.get_allocation(self.allocation_id),
            self.planned.get_allocation(self.allocation_id),
        )

    def test_plan_export_rejects_empty_duplicate_warehouse_foreign_and_cancelled_selection(
        self,
    ) -> None:
        """Корень экспортирует только принадлежащие ему целые действующие внешние строки."""
        for ids in (
            (),
            (self.allocation_id, self.allocation_id),
            (self.f.f.allocation.id,),
        ):
            with self.subTest(ids=ids), self.assertRaises(FulfillmentPlanContextError):
                self.planned.supplier_order_basis_snapshot(allocation_ids=ids)
        with self.assertRaises(FulfillmentAllocationNotFoundError):
            self.planned.supplier_order_basis_snapshot(
                allocation_ids=(FulfillmentAllocationIdVO(uuid4()),)
            )
        cancelled = self.planned.cancel_allocations(
            allocation_ids=(self.allocation_id,),
            expected_version=self.planned.version,
            updated_at=self.planned.updated_at,
        )
        with self.assertRaises(FulfillmentPlanContextError):
            cancelled.supplier_order_basis_snapshot(
                allocation_ids=(self.allocation_id,)
            )
        for invalid in (
            self.draft,
            self.planned.cancel(
                expected_version=self.planned.version,
                updated_at=self.planned.updated_at,
            ),
        ):
            with self.assertRaises(FulfillmentPlanStatusError):
                invalid.supplier_order_basis_snapshot(
                    allocation_ids=(self.allocation_id,)
                )

    def test_rejects_inactive_wrong_source_and_incompatible_offers(self) -> None:
        """Источник должен поддерживать DROPSHIP, а предложение совпадать с поставщиком, товаром и единицей."""
        for source in (
            replace(self.source, is_active=False),
            replace(self.source, supports_dropship=False),
            replace(self.source, id=ExternalSupplierSourceIdVO(uuid4())),
        ):
            with (
                self.subTest(source=source),
                self.assertRaises(SupplierFulfillmentBasisMismatchError),
            ):
                self.create(source=source)
        for changes in (
            dict(
                supplier=ExternalSupplierReferenceVO.from_value("crm.company", uuid4())
            ),
            dict(source_id=ExternalSupplierSourceIdVO(uuid4())),
            dict(is_active=False),
            dict(inventory_item_id=ExternalInventoryItemIdVO(uuid4())),
            dict(base_uom=SupplierFulfillmentUomCodeVO("KG")),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(SupplierFulfillmentBasisMismatchError),
            ):
                self.create(offers=(replace(self.offer, **changes),))
        self.create(offers=(replace(self.offer, source_id=None),))

    def test_requires_exact_unique_offers_and_line_bindings(self) -> None:
        """Фабрика требует полные однозначные соответствия без лишних идентификаторов."""
        for offers in (
            (),
            (self.offer, self.offer),
            (self.offer, replace(self.offer, id=ExternalSupplierOfferIdVO(uuid4()))),
        ):
            with (
                self.subTest(offers=offers),
                self.assertRaises(SupplierFulfillmentBasisMismatchError),
            ):
                self.create(offers=offers)
        binding = self.bindings(self.basis)[0]
        for bindings in (
            (),
            (binding, binding),
            (
                replace(
                    binding, allocation_id=ExternalFulfillmentAllocationIdVO(uuid4())
                ),
            ),
        ):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(SupplierFulfillmentBasisMismatchError),
            ):
                self.create(line_bindings=bindings)
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            self.create(
                basis=replace(self.basis, allocations=self.basis.allocations * 2)
            )

    def test_rejects_group_with_multiple_sources_even_with_valid_offers(self) -> None:
        """Выбор разных источников оформляется разными внешними черновиками."""
        another = FulfillmentAllocationIdVO(uuid4())
        alt_source = replace(
            self.f.option.source,
            supplier_source_id=FulfillmentSupplierSourceIdVO(uuid4()),
            supplier_offer_id=FulfillmentSupplierOfferIdVO(uuid4()),
        )
        alternate = replace(
            self.f.option,
            source=alt_source,
            offer_source_id=alt_source.supplier_source_id,
        )
        draft = self.f.add(
            self.draft,
            identifier=another,
            source_ref=self.f.f.other_ref,
            supplier_option=alternate,
        )
        planned = self.f.mark(draft, supplier_options=(self.f.option, alternate))
        basis = self.map_basis(planned, self.allocation_id, another)
        offer = replace(
            self.offer,
            id=basis.allocations[1].supplier_offer_id,
            source_id=basis.allocations[1].supplier_source_id,
        )
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            self.create(
                basis=basis,
                offers=(self.offer, offer),
                line_bindings=self.bindings(basis),
            )

    def test_restore_validates_local_draft_fields_and_unique_lines(self) -> None:
        """Восстановление проверяет собственную историю без текущих данных Supplier Sourcing."""
        order = self.create()
        line = order.lines[0]
        for changes in (
            dict(lines=()),
            dict(lines=(line, replace(line, id=SupplierFulfillmentLineIdVO(uuid4())))),
            dict(
                lines=(
                    line,
                    replace(
                        line,
                        fulfillment_allocation_id=ExternalFulfillmentAllocationIdVO(
                            uuid4()
                        ),
                    ),
                )
            ),
            dict(
                lines=(
                    replace(
                        line,
                        requested_quantity=SupplierFulfillmentQuantityVO(Decimal(0)),
                    ),
                )
            ),
            dict(
                lines=(
                    replace(line, quoted_price=MoneyVO(Decimal(-1), CurrencyVO("UAH"))),
                )
            ),
            dict(status="DRAFT"),
            dict(version=True),
            dict(version=1),
            dict(delivery_address=None),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidSupplierFulfillmentValueError),
            ):
                self.restore(order, **changes)
        with self.assertRaises(FrozenInstanceError):
            order.delivery_address = SupplierDeliveryAddressVO(
                "UA", "Львів", "вул. Тестова, 2"
            )

    def test_address_normalization_and_time_of_creation(self) -> None:
        """Сохраняет нормализованный адрес, UTC и порядок относительно основания."""
        self.assertEqual(
            (self.address.country_code, self.address.city, self.address.postal_code),
            ("UA", "Київ", "01001"),
        )
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            SupplierDeliveryAddressVO("UKR", "Київ", "вул. Тестова, 1")
        with self.assertRaises(InvalidSupplierFulfillmentValueError):
            SupplierDeliveryAddressVO("UA", " ", "вул. Тестова, 1")
        at = self.basis.plan_updated_at
        order = self.create(created_at=at.astimezone(timezone(timedelta(hours=2))))
        self.assertEqual(order.created_at, at)
        self.assertIs(order.created_at.tzinfo, UTC)
        for created in (at - timedelta(seconds=1), at.replace(tzinfo=None)):
            with (
                self.subTest(created=created),
                self.assertRaises(SupplierFulfillmentTimeError),
            ):
                self.create(created_at=created)
