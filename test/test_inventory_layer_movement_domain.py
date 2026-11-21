"""Перенос стоимости одного слоя по полной паре INTERNAL_MOVE."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_valuation_layer_domain as layer_fixture
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.movement_valuation_snapshot import (
    StockMovementValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.movement_entry_pair import (
    StockMovementEntryPairVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.valuation_layer.aggregate import ValuationLayer
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerBasisSnapshotError,
    InvalidValuationLayerMovementConsumptionSnapshotError,
    InvalidValuationLayerReceiptSnapshotError,
    InvalidValuationLayerTransferOriginError,
    ValuationLayerConsumptionError,
    ValuationLayerIssueMismatchError,
    ValuationLayerMovementMismatchError,
    ValuationLayerTimeError,
    ValuationLayerVersionConflictError,
)
from src.modules.inventory.domain.valuation_layer.movement_consumption_snapshot import (
    ValuationLayerMovementConsumptionSnapshot,
)
from src.modules.inventory.domain.valuation_posting.aggregate import ValuationPosting
from src.modules.inventory.domain.valuation_posting.error import (
    ValuationPostingSourceError,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_binding import (
    ValuationEntryBindingVO,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_id import (
    ValuationEntryIdVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_posting.value_object.identifier import (
    ValuationPostingIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class ValuationLayerMovementDomainTests(unittest.TestCase):
    """Проверяет перенос количества и стоимости, происхождение и дальнейший расход."""

    def setUp(self) -> None:
        """Готовит слой 10 KG за 120 UAH и пару перемещения 7 KG."""
        self.v = layer_fixture.ValuationLayerDomainTests()
        self.v.setUp()
        self.f = self.v.f
        self.layer = self.receipt_layer(self.f.first, "10", "120")
        self.moved_at = self.v.at + timedelta(days=1)
        self.registered_at = self.moved_at + timedelta(hours=1)
        self.movement = self.move(self.f.first, self.f.second, "7")

    def receipt_layer(
        self,
        position: StockPosition,
        quantity: str,
        cost: str,
        *,
        received_at: datetime | None = None,
        currency: str = "UAH",
    ) -> ValuationLayer:
        """Создаёт слой из реальной приходной записи на указанном адресе."""
        at = self.f.time if received_at is None else received_at
        location = (
            self.f.first_location
            if position.dimensions.location_id == self.f.first_location.id
            else self.f.second_location
        )
        posting = self.f.posting(
            entries=(self.f.entry(quantity, position),),
            positions=(position.snapshot(),),
            posted_at=at,
        )
        return self.v.create(
            receipt=self.v.produce(
                posting, position=position.snapshot(), location=location
            ),
            total_cost=MoneyVO(Decimal(cost), CurrencyVO(currency)),
            created_at=at,
        )

    def move(
        self, source: StockPosition, target: StockPosition, quantity: str
    ) -> StockMovementValuationSnapshot:
        """Создаёт реальную полную пару Ledger и извлекает её проверенное основание."""
        positions = (source.snapshot(), target.snapshot())
        locations = (self.f.first_location, self.f.second_location)
        outgoing = self.f.entry("-" + quantity, source)
        incoming = self.f.entry(quantity, target)
        posting = self.f.movement(
            entries=(outgoing, incoming),
            positions=positions,
            locations=locations,
            posted_at=self.moved_at,
        )
        return posting.movement_valuation_snapshot(
            pair=StockMovementEntryPairVO(outgoing.id, incoming.id),
            positions=positions,
            locations=locations,
        )

    def consume(
        self,
        layer: ValuationLayer | None = None,
        movement: StockMovementValuationSnapshot | None = None,
    ) -> tuple[ValuationLayer, ValuationLayerMovementConsumptionSnapshot]:
        """Потребляет выбранный слой с его текущей версией."""
        source = self.layer if layer is None else layer
        return source.consume_for_movement(
            self.movement if movement is None else movement,
            expected_version=source.version,
            updated_at=self.registered_at,
        )

    def destination(
        self, consumption: ValuationLayerMovementConsumptionSnapshot
    ) -> ValuationLayer:
        """Создаёт слой назначения из проверяемого перехода."""
        return ValuationLayer.create_from_movement(
            identifier=ValuationLayerIdVO(uuid4()),
            consumption=consumption,
            created_at=self.registered_at,
        )

    def destination_issue(self, issued_at: datetime) -> StockPosting:
        """Готовит физическое проведение расхода двух KG с адреса назначения."""
        return self.f.posting(
            operation_type=StockOperationType.ISSUE,
            entries=(self.f.entry("-2", self.f.second),),
            positions=(self.f.second.snapshot(),),
            posted_at=issued_at,
        )

    def test_partial_move_conserves_quantity_currency_and_cost(self) -> None:
        """Обе стороны перехода сохраняют 10 KG и 120 UAH, а исходные объекты неизменяемы."""
        source, result = self.consume()
        target = self.destination(result)
        self.assertEqual(source.remaining_qty.value, Decimal(3))
        self.assertEqual(source.remaining_cost.amount, Decimal(36))
        self.assertEqual(target.remaining_qty.value, Decimal(7))
        self.assertEqual(target.remaining_cost.amount, Decimal(84))
        self.assertEqual(
            source.remaining_cost + target.remaining_cost, self.layer.remaining_cost
        )
        self.assertEqual(target.remaining_cost, result.cost)
        self.assertEqual((source.version, target.version), (1, 0))
        self.assertEqual(source.cost_basis, self.layer.cost_basis)
        self.assertEqual(source.source, self.layer.source)
        self.assertEqual(self.layer.remaining_qty.value, Decimal(10))
        self.assertEqual(self.f.first.on_hand_qty.value, Decimal(10))
        self.assertEqual(self.f.second.on_hand_qty.value, Decimal(0))

    def test_destination_preserves_receipt_origin_and_records_both_ledger_sides(
        self,
    ) -> None:
        """Ссылка на приход сохраняется отдельно от входящей записи и даты доступности."""
        _, result = self.consume()
        layer = self.destination(result)
        basis = layer.basis_snapshot()
        self.assertEqual(basis.received_at, self.layer.received_at)
        self.assertEqual(basis.available_at, self.moved_at)
        self.assertEqual(layer.created_at, self.registered_at)
        self.assertEqual(layer.source.posting_id, self.movement.posting_id)
        self.assertEqual(
            layer.source.ledger_entry_id, self.movement.pair.incoming_entry_id
        )
        self.assertEqual(layer.source.position_id, self.f.second.id)
        self.assertEqual(layer.transfer_origin.parent_layer_id, self.layer.id)
        self.assertEqual(layer.transfer_origin.receipt_source, self.layer.source)
        self.assertEqual(
            layer.transfer_origin.outgoing_entry_id,
            self.movement.pair.outgoing_entry_id,
        )
        self.assertEqual(self.v.restore(layer), layer)
        with self.assertRaises(FrozenInstanceError):
            result.version_after = 2

    def test_full_move_preserves_free_stock_and_non_default_currency(self) -> None:
        """Весь слой уходит, включая запас с нулевой стоимостью, в исходной валюте."""
        for cost in ("0", "10.1234"):
            with self.subTest(cost=cost):
                original = self.receipt_layer(self.f.first, "7", cost, currency="USD")
                source, result = self.consume(original)
                target = self.destination(result)
                self.assertTrue(source.is_exhausted())
                self.assertEqual(
                    source.remaining_cost, MoneyVO(Decimal(0), CurrencyVO("USD"))
                )
                self.assertEqual(target.cost_basis, original.cost_basis)

    def test_move_uses_delta_of_cumulative_rounding_under_hostile_decimal_context(
        self,
    ) -> None:
        """При переносе после частичного расхода используется остаточная разница с точностью 4 знака."""
        original = self.receipt_layer(self.f.first, "12", "1")
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            before = original.consume(
                QuantityVO(Decimal(1)), expected_version=0, updated_at=self.v.at
            )
            after, result = self.consume(before)
            target = self.destination(result)
            self.assertEqual(
                after.remaining_cost + target.remaining_cost, before.remaining_cost
            )
        self.assertEqual(after.remaining_cost.amount, Decimal("0.3333"))
        self.assertEqual(target.remaining_cost.amount, Decimal("0.5834"))
        self.assertEqual((result.version_before, result.version_after), (1, 2))

    def test_rejects_unrelated_layers_and_reuse_of_posting_as_receipt_source(
        self,
    ) -> None:
        """Несовместимый учётный контекст отклоняется даже при достаточном остатке."""
        for changes in (
            dict(source=replace(self.layer.source, position_id=self.f.second.id)),
            dict(
                source=replace(self.layer.source, posting_id=self.movement.posting_id)
            ),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationLayerMovementMismatchError),
            ):
                self.consume(self.v.restore(self.layer, **changes))

    def test_requires_full_pair_and_current_version(self) -> None:
        """Недостаток остатка и устаревшая версия не дают результата переноса."""
        insufficient = self.layer.consume(
            QuantityVO(Decimal(4)), expected_version=0, updated_at=self.v.at
        )
        with self.assertRaises(ValuationLayerConsumptionError):
            self.consume(insufficient)
        with self.assertRaises(ValuationLayerVersionConflictError):
            insufficient.consume_for_movement(
                self.movement, expected_version=0, updated_at=self.registered_at
            )

    def test_requires_valid_physical_and_registration_dates(self) -> None:
        """Физическое движение, потребление и создание слоя проверяются по отдельным датам."""
        with self.assertRaises(ValuationLayerTimeError):
            self.consume(
                movement=replace(
                    self.movement,
                    moved_at=self.layer.received_at - timedelta(seconds=1),
                )
            )
        with self.assertRaises(ValuationLayerTimeError):
            self.layer.consume_for_movement(
                self.movement,
                expected_version=0,
                updated_at=self.moved_at - timedelta(seconds=1),
            )
        _, result = self.consume()
        with self.assertRaises(ValuationLayerTimeError):
            ValuationLayer.create_from_movement(
                identifier=ValuationLayerIdVO(uuid4()),
                consumption=result,
                created_at=self.moved_at,
            )

    def test_factory_revalidates_transition_before_creating_value(self) -> None:
        """Подмена количества, валюты, стоимости, даты или версии не создаёт новый слой."""
        _, result = self.consume()
        for changes in (
            dict(remaining_qty_after=QuantityVO(Decimal(2))),
            dict(remaining_cost_before=MoneyVO(Decimal(120), CurrencyVO("USD"))),
            dict(remaining_cost_after=MoneyVO(Decimal(35), CurrencyVO("UAH"))),
            dict(version_after=True),
            dict(version_after=2),
            dict(consumed_at=self.moved_at - timedelta(seconds=1)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(
                    InvalidValuationLayerMovementConsumptionSnapshotError
                ),
            ):
                self.destination(replace(result, **changes))

    def test_factory_and_restore_reject_inconsistent_origin(self) -> None:
        """Слой назначения требует нового ID, двух записей и последовательной истории."""
        _, result = self.consume()
        target = self.destination(result)
        with self.assertRaises(InvalidValuationLayerBasisSnapshotError):
            ValuationLayer.create_from_movement(
                identifier=self.layer.id,
                consumption=result,
                created_at=self.registered_at,
            )
        with self.assertRaises(InvalidValuationLayerBasisSnapshotError):
            self.v.restore(
                target,
                source=replace(
                    target.source, ledger_entry_id=self.movement.pair.outgoing_entry_id
                ),
            )
        with self.assertRaises(ValuationLayerTimeError):
            self.v.restore(target, received_at=self.registered_at)
        with self.assertRaises(InvalidValuationLayerTransferOriginError):
            replace(target.transfer_origin, parent_layer_id=self.layer.id.uuid)

    def test_serial_pair_moves_one_whole_piece(self) -> None:
        """Один серийный экземпляр полностью исчерпывает исходный слой."""
        dims = replace(self.f.first.dimensions, serial_id=StockSerialIdVO(uuid4()))
        source = self.f.position(dimensions=dims, base_uom=UomCodeVO("PCS"))
        target = self.f.position(
            dimensions=replace(dims, location_id=self.f.second_location.id),
            base_uom=UomCodeVO("PCS"),
        )
        layer = self.receipt_layer(source, "1", "20")
        movement = self.move(source, target, "1")
        after, result = self.consume(layer, movement)
        destination = self.destination(result)
        self.assertTrue(after.is_exhausted())
        self.assertEqual(destination.remaining_qty.value, Decimal(1))
        self.assertEqual(destination.base_uom, UomCodeVO("PCS"))
        self.assertEqual(destination.remaining_cost.amount, Decimal(20))
        doubled = QuantityVO(Decimal(2))
        invalid_layer = self.v.restore(
            layer,
            cost_basis=replace(layer.cost_basis, quantity=doubled),
            remaining_qty=doubled,
        )
        with self.assertRaises(ValuationLayerMovementMismatchError):
            self.consume(invalid_layer, movement)

    def test_direct_issue_rejects_before_arrival_and_wrong_position(self) -> None:
        """Старая FIFO-дата не разрешает расход до перемещения или с исходного адреса."""
        _, result = self.consume()
        target = self.destination(result)
        posting = self.destination_issue(self.moved_at - timedelta(seconds=1))
        issue = posting.issue_valuation_snapshot(
            ledger_entry_id=posting.entries[0].id,
            position=self.f.second.snapshot(),
            location=self.f.second_location,
        )
        with self.assertRaises(ValuationLayerTimeError):
            target.consume_from_issue(
                issue, expected_version=0, updated_at=self.registered_at
            )
        with self.assertRaises(ValuationLayerTimeError):
            posting.issue_fifo_plan(
                candidates=(target.fifo_snapshot(),),
                positions=(self.f.second.snapshot(),),
                locations=(self.f.second_location,),
            )
        with self.assertRaises(ValuationLayerIssueMismatchError):
            self.layer.consume_from_issue(
                issue, expected_version=0, updated_at=self.registered_at
            )

    def test_destination_participates_in_full_issue_fifo_and_valuation_posting(
        self,
    ) -> None:
        """Перемещённый слой расходуется первым по дате закупки и проходит проверку расходного журнала."""
        _, result = self.consume()
        target = self.destination(result)
        competing = self.receipt_layer(self.f.second, "3", "60", received_at=self.v.at)
        posting = self.destination_issue(self.moved_at)
        positions = (self.f.second.snapshot(),)
        locations = (self.f.second_location,)
        plan = posting.issue_fifo_plan(
            candidates=(competing.fifo_snapshot(), target.fifo_snapshot()),
            positions=positions,
            locations=locations,
        )
        self.assertEqual(
            [value.layer_id for value in plan.plans[0].allocations], [target.id]
        )
        after, consumed = target.consume_fifo_allocation(
            plan.plans[0], updated_at=self.registered_at
        )
        valuation = ValuationPosting.create_from_fifo_plan(
            identifier=ValuationPostingIdVO(uuid4()),
            plan=plan,
            posting=posting.snapshot(),
            consumptions=(consumed,),
            entry_bindings=(
                ValuationEntryBindingVO(target.id, ValuationEntryIdVO(uuid4())),
            ),
            positions=positions,
            locations=locations,
            posted_at=self.registered_at,
        )
        self.assertEqual(after.remaining_qty.value, Decimal(5))
        self.assertEqual(after.remaining_cost.amount, Decimal(60))
        self.assertEqual(valuation.entries[0].layer_id, target.id)
        self.assertEqual(valuation.entries[0].cost_delta.amount, Decimal(-24))

    def test_purchase_journal_and_second_movement_reject_derived_layer(self) -> None:
        """Текущий срез поддерживает один перенос из слоя закупочного прихода."""
        _, result = self.consume()
        target = self.destination(result)
        with self.assertRaises(InvalidValuationLayerReceiptSnapshotError):
            target.receipt_valuation_snapshot()
        with self.assertRaises(ValuationPostingSourceError):
            ValuationPosting.create_from_receipt(
                identifier=ValuationPostingIdVO(uuid4()),
                posting=self.v.posting.snapshot(),
                layers=(target.basis_snapshot(),),
                entry_bindings=(),
                positions=(self.f.first.snapshot(),),
                locations=(self.f.first_location,),
                posted_at=self.registered_at,
            )
        with self.assertRaises(ValuationLayerMovementMismatchError):
            self.consume(target, self.move(self.f.second, self.f.first, "2"))
