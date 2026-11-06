"""Ручное распределение потребности заказа по собственным складам без резервов и отгрузки."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from src.modules.inventory.domain.error import InventoryError, QuantityStepError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.demand_snapshot import (
    FulfillmentDemandSnapshot,
    FulfillmentDemandLineSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    EmptyFulfillmentPlanError,
    FulfillmentAllocationConflictError,
    FulfillmentAllocationNotFoundError,
    FulfillmentDemandExceededError,
    FulfillmentOrderUnavailableError,
    FulfillmentPlanContextError,
    FulfillmentPlanStatusError,
    FulfillmentPlanTimeError,
    FulfillmentPlanVersionConflictError,
    FulfillmentSourceSplitForbiddenError,
    InvalidFulfillmentAllocationError,
    InvalidFulfillmentDemandError,
    InvalidFulfillmentOrderRefError,
    InvalidFulfillmentPlanValueError,
    InvalidFulfillmentSourceError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.order_ref import (
    FulfillmentOrderRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_kind import (
    FulfillmentSourceKind,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_ref import (
    FulfillmentSourceRefVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class FulfillmentPlanDomainTests(unittest.TestCase):
    """Проверяет локальные инварианты, текущую потребность и жизненный цикл самостоятельного плана."""

    def setUp(self) -> None:
        """Готовит две строки одного заказа, один товар и два активных склада без физических остатков."""
        self.time = datetime(2026, 11, 6, 12, tzinfo=UTC)
        self.order_ref = FulfillmentOrderRefVO("orders", "000042")
        self.owner = StockOwnerIdVO(uuid4())
        self.a = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.b = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.item = InventoryItemStockSnapshot(
            InventoryItemIdVO(uuid4()),
            UomCodeVO("PCS"),
            QuantityRulesVO(Decimal(1)),
            TrackingMode.NONE,
        )
        self.source = FulfillmentSourceRefVO(
            FulfillmentSourceKind.OWN_WAREHOUSE, self.a.id
        )
        self.line_ref = ReservationSourceVO("order_line", "opaque-line-A")
        self.other_ref = ReservationSourceVO(
            "external-row", "does-not-contain-order-number"
        )
        self.first_demand = FulfillmentDemandLineSnapshot(
            self.line_ref,
            self.item.inventory_item_id,
            self.item.base_uom,
            QuantityVO(Decimal(7)),
            True,
        )
        self.other_demand = replace(
            self.first_demand,
            source_ref=self.other_ref,
            remaining_qty=QuantityVO(Decimal(5)),
        )
        self.demand = FulfillmentDemandSnapshot(
            self.order_ref, True, (self.first_demand, self.other_demand)
        )
        self.draft = self.create()
        self.allocation = self.create_allocation()
        self.one = self.add(self.draft, self.allocation)

    def create(self, **changes: object) -> FulfillmentPlan:
        """Создаёт пустой черновик с явными идентификаторами и временем."""
        return FulfillmentPlan.create(
            **(
                dict(
                    identifier=FulfillmentPlanIdVO(uuid4()),
                    order_ref=self.order_ref,
                    owner_id=self.owner,
                    created_at=self.time,
                )
                | changes
            )
        )

    def create_allocation(self, **changes: object) -> FulfillmentAllocation:
        """Создаёт положительную строку в базовой единице по текущим правилам товара."""
        return FulfillmentAllocation.create(
            **(
                dict(
                    identifier=FulfillmentAllocationIdVO(uuid4()),
                    source_ref=self.line_ref,
                    inventory_item=self.item,
                    source=self.source,
                    quantity=QuantityVO(Decimal(3)),
                )
                | changes
            )
        )

    def add(
        self,
        plan: FulfillmentPlan,
        allocation: FulfillmentAllocation,
        **changes: object,
    ) -> FulfillmentPlan:
        """Передаёт текущую потребность и ровно контекст добавляемого распределения."""
        warehouse = self.a if allocation.source.warehouse_id == self.a.id else self.b
        return plan.add_allocation(
            allocation,
            **(
                dict(
                    demand=self.demand,
                    inventory_item=self.item,
                    warehouse=warehouse,
                    expected_version=plan.version,
                    updated_at=self.time + timedelta(minutes=1),
                )
                | changes
            ),
        )

    def mark(
        self, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Фиксирует план по всему актуальному набору товаров и складов."""
        target = self.one if plan is None else plan
        by_warehouse = {self.a.id: self.a, self.b.id: self.b}
        warehouses = tuple(
            by_warehouse.get(identifier)
            for identifier in {
                allocation.source.warehouse_id for allocation in target.allocations
            }
        )
        return target.mark_planned(
            **(
                dict(
                    demand=self.demand,
                    inventory_items=(self.item,),
                    warehouses=warehouses,
                    expected_version=target.version,
                    updated_at=self.time + timedelta(minutes=2),
                )
                | changes
            )
        )

    def change(self, quantity: str, **changes: object) -> FulfillmentPlan:
        """Меняет количество первой строки черновика по его текущей версии."""
        return self.one.change_allocation_quantity(
            **(
                dict(
                    identifier=self.allocation.id,
                    quantity=QuantityVO(Decimal(quantity)),
                    demand=self.demand,
                    inventory_item=self.item,
                    warehouse=self.a,
                    expected_version=self.one.version,
                    updated_at=self.time + timedelta(minutes=2),
                )
                | changes
            )
        )

    def restore(self, plan: FulfillmentPlan, **changes: object) -> FulfillmentPlan:
        """Восстанавливает только собственные исторические значения агрегата."""
        values = {field.name: getattr(plan, field.name) for field in fields(plan)}
        values["identifier"] = values.pop("id")
        return FulfillmentPlan.restore(**(values | changes))

    def test_create_is_empty_owned_draft_without_external_commitments(self) -> None:
        """Черновик фиксирует заказ и владельца, версия ноль и пустой состав не требуют резервов или позиций."""
        self.assertEqual(self.draft.status, FulfillmentPlanStatus.DRAFT)
        self.assertEqual(self.draft.version, 0)
        self.assertEqual(self.draft.allocations, ())
        self.assertEqual(self.draft.order_ref, self.order_ref)
        self.assertEqual(self.draft.owner_id, self.owner)
        self.assertEqual(self.draft.created_at, self.draft.updated_at)
        self.assertEqual(
            self.draft.remaining_to_allocate(self.line_ref, demand=self.demand).value, 7
        )
        with self.assertRaises(FrozenInstanceError):
            self.draft.owner_id = StockOwnerIdVO(uuid4())

    def test_seven_pieces_split_three_and_four_across_own_warehouses(self) -> None:
        """Три с A и четыре с B покрывают семь; PLANNED фиксирует намерение, сохраняя исходные экземпляры."""
        other = self.create_allocation(
            source=replace(self.source, warehouse_id=self.b.id),
            quantity=QuantityVO(Decimal(4)),
        )
        split = self.add(self.one, other)
        planned = self.mark(split)
        self.assertEqual(planned.status, FulfillmentPlanStatus.PLANNED)
        self.assertEqual(planned.version, 3)
        self.assertEqual(
            planned.remaining_to_allocate(self.line_ref, demand=self.demand).value, 0
        )
        self.assertEqual(
            planned.remaining_to_allocate(self.other_ref, demand=self.demand).value, 5
        )
        self.assertEqual(
            {allocation.source.warehouse_id for allocation in planned.allocations},
            {self.a.id, self.b.id},
        )
        self.assertEqual(self.draft.allocations, ())
        self.assertEqual(self.one.allocations, (self.allocation,))
        self.assertEqual(self.one.status, FulfillmentPlanStatus.DRAFT)

    def test_partial_plan_and_unsplit_source_are_allowed(self) -> None:
        """Незапланированный остаток допустим даже при запрете разделять источники."""
        demand = replace(
            self.demand,
            lines=(
                replace(self.first_demand, allow_source_split=False),
                self.other_demand,
            ),
        )
        planned = self.mark(demand=demand)
        self.assertEqual(
            planned.remaining_to_allocate(self.line_ref, demand=demand).value, 4
        )

    def test_three_plus_five_exceeds_remaining_demand_without_changing_root(
        self,
    ) -> None:
        """Сумма по всем складам одной строки ограничена текущей потребностью."""
        other = self.create_allocation(
            source=replace(self.source, warehouse_id=self.b.id),
            quantity=QuantityVO(Decimal(5)),
        )
        with self.assertRaises(FulfillmentDemandExceededError):
            self.add(self.one, other)
        self.assertEqual(self.one.allocations, (self.allocation,))
        with self.assertRaises(FulfillmentDemandExceededError):
            self.change("8")

    def test_split_flag_is_checked_on_add_and_again_on_mark(self) -> None:
        """Новый запрет разделения не позволяет зафиксировать ранее подготовленное распределение."""
        other = self.create_allocation(
            source=replace(self.source, warehouse_id=self.b.id),
            quantity=QuantityVO(Decimal(4)),
        )
        no_split = replace(
            self.demand, lines=(replace(self.first_demand, allow_source_split=False),)
        )
        with self.assertRaises(FulfillmentSourceSplitForbiddenError):
            self.add(self.one, other, demand=no_split)
        split = self.add(self.one, other)
        with self.assertRaises(FulfillmentSourceSplitForbiddenError):
            self.mark(split, demand=no_split)

    def test_one_source_pair_and_one_identifier_are_unique(self) -> None:
        """Повтор пары строка/источник и повтор ID запрещены независимо от оставшейся потребности."""
        for other in (
            replace(self.allocation, id=FulfillmentAllocationIdVO(uuid4())),
            replace(
                self.allocation, source=replace(self.source, warehouse_id=self.b.id)
            ),
        ):
            with (
                self.subTest(allocation=other),
                self.assertRaises(FulfillmentAllocationConflictError),
            ):
                self.add(self.one, other)

    def test_two_order_lines_may_use_same_item_and_same_warehouse(self) -> None:
        """Обязательства разных строк не объединяются по SKU или выбранному складу."""
        other = self.create_allocation(
            source_ref=self.other_ref, quantity=QuantityVO(Decimal(5))
        )
        planned = self.mark(self.add(self.one, other))
        self.assertEqual(len(planned.allocations), 2)
        self.assertEqual(
            planned.remaining_to_allocate(self.line_ref, demand=self.demand).value, 4
        )
        self.assertEqual(
            planned.remaining_to_allocate(self.other_ref, demand=self.demand).value, 0
        )

    def test_order_ownership_uses_snapshot_membership_not_reference_parsing(
        self,
    ) -> None:
        """Произвольный формат ссылки допустим, но отсутствующая строка или чужой заказ отклоняются."""
        valid = self.create_allocation(source_ref=self.other_ref)
        self.add(self.draft, valid)
        foreign = self.create_allocation(
            source_ref=ReservationSourceVO("order_line", "000042:foreign")
        )
        with self.assertRaises(FulfillmentPlanContextError):
            self.add(self.draft, foreign)
        with self.assertRaises(FulfillmentPlanContextError):
            self.mark(
                demand=replace(
                    self.demand, order_ref=FulfillmentOrderRefVO("orders", "other")
                )
            )

    def test_cancelled_or_closed_order_cannot_be_planned(self) -> None:
        """Недоступность заказа блокирует новые распределения, изменение количества и фиксацию."""
        unavailable = replace(self.demand, is_fulfillable=False)
        for operation in (
            lambda: self.add(self.draft, self.allocation, demand=unavailable),
            lambda: self.change("4", demand=unavailable),
            lambda: self.mark(demand=unavailable),
        ):
            with self.assertRaises(FulfillmentOrderUnavailableError):
                operation()
        self.one.remove_allocation(
            self.allocation.id,
            expected_version=self.one.version,
            updated_at=self.one.updated_at,
        )

    def test_changed_demand_is_revalidated_at_mark_and_remaining_query(self) -> None:
        """Уменьшение остатка, удаление строки или новая идентичность делают прежний черновик несовместимым."""
        for demand in (
            replace(
                self.demand,
                lines=(
                    replace(self.first_demand, remaining_qty=QuantityVO(Decimal(2))),
                ),
            ),
            replace(self.demand, lines=(self.other_demand,)),
            replace(
                self.demand,
                lines=(
                    replace(
                        self.first_demand, inventory_item_id=InventoryItemIdVO(uuid4())
                    ),
                ),
            ),
            replace(
                self.demand,
                lines=(replace(self.first_demand, base_uom=UomCodeVO("KG")),),
            ),
        ):
            with self.subTest(demand=demand):
                with self.assertRaises(InventoryError):
                    self.mark(demand=demand)
                with self.assertRaises(InventoryError):
                    self.one.remaining_to_allocate(self.line_ref, demand=demand)

    def test_zero_demand_line_cannot_receive_positive_allocation(self) -> None:
        """Нулевой остаток корректен как вход заказа, но не допускает новое распределение."""
        demand = replace(
            self.demand,
            lines=(replace(self.first_demand, remaining_qty=QuantityVO(Decimal(0))),),
        )
        demand.ensure_valid()
        with self.assertRaises(FulfillmentDemandExceededError):
            self.add(self.draft, self.allocation, demand=demand)

    def test_allocation_factory_and_restore_require_positive_base_quantity(
        self,
    ) -> None:
        """Ноль и сырое число не становятся намерением исполнения, а историческая единица известна каталогу."""
        for quantity in (QuantityVO(Decimal(0)), Decimal(3), None):
            with (
                self.subTest(quantity=quantity),
                self.assertRaises(InvalidFulfillmentAllocationError),
            ):
                self.create_allocation(quantity=quantity)
        with self.assertRaises(FrozenInstanceError):
            self.allocation.quantity = QuantityVO(Decimal(5))

    def test_quantity_step_is_checked_at_creation_edit_and_mark(self) -> None:
        """Новый шаг не округляет старую строку и требует исправления до фиксации."""
        item = replace(self.item, quantity_rules=QuantityRulesVO(Decimal(2)))
        with self.assertRaises(QuantityStepError):
            self.create_allocation(inventory_item=item)
        with self.assertRaises(QuantityStepError):
            self.change("3", inventory_item=item)
        with self.assertRaises(QuantityStepError):
            self.mark(inventory_items=(item,))
        changed = self.change("4", inventory_item=item)
        self.assertEqual(
            self.mark(changed, inventory_items=(item,)).allocations[0].quantity.value, 4
        )

    def test_item_or_base_uom_change_is_not_silently_reinterpreted(self) -> None:
        """Смена карточки либо базовой единицы не пересчитывает историческое намерение автоматически."""
        for item in (
            replace(self.item, inventory_item_id=InventoryItemIdVO(uuid4())),
            replace(self.item, base_uom=UomCodeVO("KG")),
        ):
            with (
                self.subTest(item=item),
                self.assertRaises(FulfillmentPlanContextError),
            ):
                self.change("4", inventory_item=item)
        with self.assertRaises(FulfillmentPlanContextError):
            self.add(self.draft, self.allocation, warehouse=self.b)

    def test_serial_modes_plan_whole_pieces_without_selecting_serial_ids(self) -> None:
        """SERIAL и LOT_AND_SERIAL допускают план семи экземпляров и сохраняют step=1/PCS."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = replace(self.item, tracking_mode=mode)
            allocation = self.create_allocation(
                inventory_item=item, quantity=QuantityVO(Decimal(7))
            )
            plan = self.add(self.draft, allocation, inventory_item=item)
            self.mark(plan, inventory_items=(item,))
            with self.assertRaises(QuantityStepError):
                self.create_allocation(
                    inventory_item=item, quantity=QuantityVO(Decimal("0.5"))
                )

    def test_weight_quantity_and_remaining_are_exact_under_small_decimal_context(
        self,
    ) -> None:
        """Суммы и остатки не зависят от глобальной точности Decimal и не округляются."""
        item = replace(
            self.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.01")),
        )
        demand = replace(
            self.demand,
            lines=(
                replace(
                    self.first_demand,
                    base_uom=item.base_uom,
                    remaining_qty=QuantityVO(Decimal("123.45")),
                ),
            ),
        )
        first = self.create_allocation(
            inventory_item=item, quantity=QuantityVO(Decimal("120.12"))
        )
        second = self.create_allocation(
            inventory_item=item,
            source=replace(self.source, warehouse_id=self.b.id),
            quantity=QuantityVO(Decimal("3.33")),
        )
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = context.traps[Rounded] = True
            one = self.add(self.draft, first, inventory_item=item, demand=demand)
            self.assertEqual(
                one.remaining_to_allocate(self.line_ref, demand=demand).value,
                Decimal("3.33"),
            )
            two = self.add(one, second, inventory_item=item, demand=demand)
            self.mark(two, inventory_items=(item,), demand=demand)
            self.assertEqual(
                two.remaining_to_allocate(self.line_ref, demand=demand).value, 0
            )

    def test_mark_requires_exact_unique_item_and_warehouse_context(self) -> None:
        """Пропуски, дубли, сырые значения и лишние текущие снимки не допускаются."""
        for items in (
            (),
            (self.item, self.item),
            (None,),
            list((self.item,)),
            (
                self.item,
                replace(self.item, inventory_item_id=InventoryItemIdVO(uuid4())),
            ),
        ):
            with self.subTest(items=items), self.assertRaises(InventoryError):
                self.mark(inventory_items=items)
        for warehouses in (
            (),
            (self.a, self.a),
            (None,),
            list((self.a,)),
            (self.a, self.b),
        ):
            with self.subTest(warehouses=warehouses), self.assertRaises(InventoryError):
                self.mark(warehouses=warehouses)

    def test_warehouse_inactivity_is_checked_on_add_edit_and_finalization(self) -> None:
        """Планирование требует активный склад, но не требует основной локации или данных о запасе."""
        inactive = replace(self.a, is_active=False)
        for operation in (
            lambda: self.add(self.draft, self.allocation, warehouse=inactive),
            lambda: self.change("4", warehouse=inactive),
            lambda: self.mark(warehouses=(inactive,)),
        ):
            with self.assertRaises(WarehouseInactiveError):
                operation()
        self.assertEqual(self.mark().status, FulfillmentPlanStatus.PLANNED)

    def test_change_preserves_source_order_line_identity_and_base_unit(self) -> None:
        """Изменение количества сохраняет все привязки и увеличивает версию один раз."""
        changed = self.change("4")
        allocation = changed.get_allocation(self.allocation.id)
        self.assertEqual(
            allocation, replace(self.allocation, quantity=QuantityVO(Decimal(4)))
        )
        self.assertEqual(changed.version, self.one.version + 1)
        self.assertEqual(changed.order_ref, self.one.order_ref)
        self.assertEqual(changed.owner_id, self.one.owner_id)
        self.assertEqual(self.one.allocations[0].quantity.value, 3)

    def test_equal_quantity_is_noop_only_after_current_checks(self) -> None:
        """Равный ввод не обновляет время/версию, но не обходит новый шаг или текущий лимит заказа."""
        self.assertIs(self.change("3.00"), self.one)
        with self.assertRaises(FulfillmentDemandExceededError):
            self.change(
                "3.00",
                demand=replace(
                    self.demand,
                    lines=(
                        replace(
                            self.first_demand, remaining_qty=QuantityVO(Decimal(2))
                        ),
                    ),
                ),
            )
        with self.assertRaises(QuantityStepError):
            self.change(
                "3.00",
                inventory_item=replace(
                    self.item, quantity_rules=QuantityRulesVO(Decimal(2))
                ),
            )

    def test_remove_can_empty_draft_without_current_external_context(self) -> None:
        """Удаление намерения не требует заказа/склада и не освобождает внешнее удержание."""
        empty = self.one.remove_allocation(
            self.allocation.id,
            expected_version=self.one.version,
            updated_at=self.one.updated_at,
        )
        self.assertEqual(empty.allocations, ())
        self.assertEqual(empty.version, self.one.version + 1)
        with self.assertRaises(EmptyFulfillmentPlanError):
            self.mark(empty, inventory_items=(), warehouses=())

    def test_missing_or_raw_allocation_id_is_rejected(self) -> None:
        """Entity загружается только через свой корень по типизированному существующему ID."""
        with self.assertRaises(FulfillmentAllocationNotFoundError):
            self.one.get_allocation(FulfillmentAllocationIdVO(uuid4()))
        with self.assertRaises(InvalidFulfillmentAllocationError):
            self.one.get_allocation(str(self.allocation.id.uuid))

    def test_mark_requires_nonempty_plan(self) -> None:
        """Пустой черновик нельзя зафиксировать даже при корректной потребности заказа."""
        with self.assertRaises(EmptyFulfillmentPlanError):
            self.mark(self.draft, inventory_items=(), warehouses=())

    def test_planned_is_immutable_and_cancelled_history_is_readable(self) -> None:
        """Редактирование и повторная фиксация запрещены; отмена сохраняет историю без текущего контекста."""
        planned = self.mark()
        for plan in (
            planned,
            planned.cancel(
                expected_version=planned.version, updated_at=planned.updated_at
            ),
        ):
            with self.subTest(status=plan.status):
                with self.assertRaises(FulfillmentPlanStatusError):
                    self.add(plan, self.create_allocation(source_ref=self.other_ref))
                with self.assertRaises(FulfillmentPlanStatusError):
                    plan.remove_allocation(
                        self.allocation.id,
                        expected_version=plan.version,
                        updated_at=plan.updated_at,
                    )
                with self.assertRaises(FulfillmentPlanStatusError):
                    self.mark(plan)
                self.assertEqual(
                    plan.get_allocation(self.allocation.id), self.allocation
                )
        cancelled = planned.cancel(
            expected_version=planned.version, updated_at=planned.updated_at
        )
        with self.assertRaises(FulfillmentPlanStatusError):
            cancelled.cancel(
                expected_version=cancelled.version, updated_at=cancelled.updated_at
            )
        with self.assertRaises(FulfillmentPlanStatusError):
            cancelled.remaining_to_allocate(self.line_ref, demand=self.demand)

    def test_cancel_draft_or_planned_preserves_composition_and_does_not_need_demand(
        self,
    ) -> None:
        """Отмена доступна обоим активным статусам и не удаляет распределения или внешний заказ."""
        for plan in (self.draft, self.one, self.mark()):
            cancelled = plan.cancel(
                expected_version=plan.version, updated_at=plan.updated_at
            )
            self.assertEqual(cancelled.status, FulfillmentPlanStatus.CANCELLED)
            self.assertEqual(cancelled.allocations, plan.allocations)
            self.assertEqual(cancelled.version, plan.version + 1)
            self.assertEqual(self.restore(cancelled), cancelled)

    def test_restore_checks_intrinsic_composition_without_current_snapshots(
        self,
    ) -> None:
        """Восстановление не требует текущих правил, но не допускает повторов и разных товаров одной строки."""
        planned = self.mark()
        self.assertEqual(self.restore(planned), planned)
        other_item = replace(
            self.allocation,
            id=FulfillmentAllocationIdVO(uuid4()),
            source=replace(self.source, warehouse_id=self.b.id),
            inventory_item_id=InventoryItemIdVO(uuid4()),
        )
        for changes in (
            dict(allocations=()),
            dict(allocations=list(planned.allocations)),
            dict(allocations=(None,)),
            dict(allocations=(self.allocation, self.allocation)),
            dict(allocations=(self.allocation, other_item)),
            dict(version=True),
            dict(owner_id="owner"),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.restore(planned, **changes)

    def test_restore_can_read_old_quantity_while_mark_checks_new_step(self) -> None:
        """Историческое значение не нормализуется по новым правилам, актуальная проверка выполняется при фиксации."""
        restored = self.restore(self.one)
        self.assertEqual(restored.allocations[0].quantity.value, 3)
        with self.assertRaises(QuantityStepError):
            self.mark(
                restored,
                inventory_items=(
                    replace(self.item, quantity_rules=QuantityRulesVO(Decimal(2))),
                ),
            )

    def test_expected_version_is_strict_and_checked_on_every_mutation(self) -> None:
        """Устаревшая, булева и отрицательная версии не допускают изменение даже при равном содержимом."""
        for version in (True, -1, 0, Decimal(1)):
            for operation in (
                lambda: self.change("3", expected_version=version),
                lambda: self.mark(expected_version=version),
                lambda: self.one.remove_allocation(
                    self.allocation.id,
                    expected_version=version,
                    updated_at=self.one.updated_at,
                ),
                lambda: self.one.cancel(
                    expected_version=version, updated_at=self.one.updated_at
                ),
            ):
                with self.subTest(version=version), self.assertRaises(InventoryError):
                    operation()
        with self.assertRaises(FulfillmentPlanVersionConflictError):
            self.mark(expected_version=0)
        invalid = replace(self.one, version=True)
        with self.assertRaises(InvalidFulfillmentPlanValueError):
            invalid.cancel(expected_version=True, updated_at=self.one.updated_at)

    def test_time_is_explicit_normalized_and_monotone(self) -> None:
        """UTC хранится после нормализации, равные моменты разрешены, наивные и убывающие даты запрещены."""
        shifted = self.time.astimezone(timezone(timedelta(hours=3)))
        self.assertEqual(self.create(created_at=shifted).created_at, self.time)
        self.assertEqual(self.one.updated_at.utcoffset(), timedelta(0))
        with self.assertRaises(FulfillmentPlanTimeError):
            self.create(created_at=self.time.replace(tzinfo=None))
        with self.assertRaises(FulfillmentPlanTimeError):
            self.mark(updated_at=self.time)
        with self.assertRaises(FulfillmentPlanTimeError):
            self.restore(self.one, updated_at=self.time - timedelta(seconds=1))

    def test_order_reference_preserves_case_and_leading_zeros_and_rejects_controls(
        self,
    ) -> None:
        """Непрозрачные внешние ссылки нормализуют края, сохраняя значимые символы источника."""
        self.assertEqual(
            FulfillmentOrderRefVO(" Orders ", " 000042 "),
            FulfillmentOrderRefVO("Orders", "000042"),
        )
        self.assertNotEqual(
            FulfillmentOrderRefVO("orders", "abc"),
            FulfillmentOrderRefVO("orders", "ABC"),
        )
        for value in ("", "   ", "line\n", "x\u200by", None, 42):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidFulfillmentOrderRefError),
            ):
                FulfillmentOrderRefVO("orders", value)

    def test_source_accepts_only_implemented_own_warehouse_kind_and_typed_id(
        self,
    ) -> None:
        """Неизвестный, сырой или ещё не реализованный источник не проходит как собственный склад."""
        for kind, warehouse in (
            ("OWN_WAREHOUSE", self.a.id),
            ("SUPPLIER_DROPSHIP", self.a.id),
            (None, self.a.id),
            (FulfillmentSourceKind.OWN_WAREHOUSE, str(self.a.id.uuid)),
        ):
            with (
                self.subTest(kind=kind, warehouse=warehouse),
                self.assertRaises(InvalidFulfillmentSourceError),
            ):
                FulfillmentSourceRefVO(kind, warehouse)

    def test_demand_snapshot_requires_nominal_values_booleans_and_unique_refs(
        self,
    ) -> None:
        """Публичная граница проверяет tuple, настоящий bool, локальные типы и единственную принадлежность строки."""
        for demand in (
            replace(self.demand, is_fulfillable=1),
            replace(self.demand, lines=list(self.demand.lines)),
            replace(self.demand, lines=(self.first_demand, self.first_demand)),
            replace(self.demand, lines=(None,)),
            replace(
                self.demand, lines=(replace(self.first_demand, allow_source_split=1),)
            ),
            replace(
                self.demand,
                lines=(replace(self.first_demand, remaining_qty=Decimal(7)),),
            ),
            replace(self.demand, order_ref=self.line_ref),
        ):
            with (
                self.subTest(demand=demand),
                self.assertRaises(InvalidFulfillmentDemandError),
            ):
                demand.ensure_valid()
        replace(self.demand, lines=()).ensure_valid()


if __name__ == "__main__":
    unittest.main()
