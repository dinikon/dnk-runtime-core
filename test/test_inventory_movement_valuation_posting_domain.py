"""Стоимостное проведение INTERNAL_MOVE по одной полной паре Ledger."""

import unittest
from dataclasses import replace
from datetime import UTC, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_layer_movement_domain as movement_fixture
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidPostingContextError,
    StockMovementValuationSourceError,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
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
    InvalidValuationLayerMovementConsumptionSnapshotError,
)
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_posting.aggregate import ValuationPosting
from src.modules.inventory.domain.valuation_posting.error import (
    DuplicateValuationEntryError,
    InvalidValuationPostingValueError,
    ValuationPostingSourceError,
    ValuationPostingTimeError,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_binding import (
    ValuationEntryBindingVO,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_id import (
    ValuationEntryIdVO,
)
from src.modules.inventory.domain.valuation_posting.value_object.identifier import (
    ValuationPostingIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class MovementValuationPostingDomainTests(unittest.TestCase):
    """Проверяет полное покрытие Ledger, происхождение и сохранение стоимости."""

    def setUp(self) -> None:
        """Готовит физическое перемещение 7 KG из слоя 10 KG стоимостью 120 UAH."""
        self.m = movement_fixture.ValuationLayerMovementDomainTests()
        self.m.setUp()
        self.f = self.m.f
        self.source = self.m.layer
        self.at = self.m.registered_at + timedelta(hours=1)
        self.prepare(self.f.first, self.f.second, self.source, "7")

    def prepare(
        self,
        source: StockPosition,
        target: StockPosition,
        layer: ValuationLayer,
        quantity: str,
    ) -> None:
        """Строит физическое проведение и оба слоя через публичные фабрики."""
        self.positions = (source.snapshot(), target.snapshot())
        self.locations = (self.f.first_location, self.f.second_location)
        outgoing = self.f.entry("-" + quantity, source)
        incoming = self.f.entry(quantity, target)
        self.posting = self.f.movement(
            entries=(incoming, outgoing),
            positions=self.positions,
            posted_at=self.m.moved_at,
        )
        self.movement = self.posting.movement_valuation_snapshot(
            pair=StockMovementEntryPairVO(outgoing.id, incoming.id),
            positions=self.positions,
            locations=self.locations,
        )
        self.source_after, self.consumption = self.m.consume(layer, self.movement)
        self.target = self.m.destination(self.consumption)
        self.bindings = (
            ValuationEntryBindingVO(self.target.id, ValuationEntryIdVO(uuid4())),
            ValuationEntryBindingVO(layer.id, ValuationEntryIdVO(uuid4())),
        )
        self.identifier = ValuationPostingIdVO(uuid4())

    def create(self, **changes: object) -> ValuationPosting:
        """Регистрирует пару с проверкой её физического контекста и первоначальной оценки."""
        return ValuationPosting.create_from_movement(
            **(
                dict(
                    identifier=self.identifier,
                    posting=self.posting.snapshot(),
                    consumption=self.consumption,
                    destination=self.target.basis_snapshot(),
                    entry_bindings=self.bindings,
                    positions=self.positions,
                    locations=self.locations,
                    posted_at=self.at,
                )
                | changes
            )
        )

    def restore(self, journal: ValuationPosting, **changes: object) -> ValuationPosting:
        """Восстанавливает журнал только по его собственным сохранённым полям."""
        return ValuationPosting.restore(
            **(
                dict(
                    identifier=journal.id,
                    stock_posting_id=journal.stock_posting_id,
                    operation_type=journal.operation_type,
                    stock_posted_at=journal.stock_posted_at,
                    posted_at=journal.posted_at,
                    entries=journal.entries,
                )
                | changes
            )
        )

    def test_creates_balanced_entries_with_exact_ledger_and_layer_references(
        self,
    ) -> None:
        """Журнал содержит выбытие и поступление с привязками независимо от порядка входов."""
        journal = self.create(
            posted_at=self.at.astimezone(timezone(timedelta(hours=2)))
        )
        self.assertEqual(journal.id, self.identifier)
        self.assertEqual(journal.stock_posting_id, self.posting.id)
        self.assertIs(journal.operation_type, StockOperationType.INTERNAL_MOVE)
        self.assertEqual(journal.stock_posted_at, self.posting.posted_at)
        self.assertEqual(journal.posted_at, self.at)
        self.assertIs(journal.posted_at.tzinfo, UTC)
        outgoing, incoming = journal.entries
        for entry, layer, binding, ledger, quantity, cost in (
            (outgoing, self.source, self.bindings[1], self.posting.entries[1], -7, -84),
            (incoming, self.target, self.bindings[0], self.posting.entries[0], 7, 84),
        ):
            self.assertEqual(entry.id, binding.entry_id)
            self.assertEqual(entry.ledger_entry_id, ledger.id)
            self.assertEqual(entry.position_id, ledger.position_id)
            self.assertEqual(entry.layer_id, layer.id)
            self.assertEqual(entry.quantity_delta.value, Decimal(quantity))
            self.assertEqual(
                entry.cost_delta, MoneyVO(Decimal(cost), CurrencyVO("UAH"))
            )
        self.assertEqual(self.restore(journal), journal)
        self.assertEqual(self.source_after.version, 1)
        self.assertEqual(self.target.version, 0)

    def test_registers_original_destination_basis_after_subsequent_issue(self) -> None:
        """Расход назначения не влияет на сумму исторического переноса."""
        issue = self.m.destination_issue(self.at)
        basis = issue.issue_valuation_snapshot(
            ledger_entry_id=issue.entries[0].id,
            position=self.positions[1],
            location=self.locations[1],
        )
        after, _ = self.target.consume_from_issue(
            basis, expected_version=0, updated_at=self.at
        )
        journal = self.create(destination=after.basis_snapshot())
        self.assertEqual(after.remaining_cost.amount, Decimal(60))
        self.assertEqual(journal.entries[1].cost_delta.amount, Decimal(84))

    def test_serial_and_zero_value_preserve_one_whole_piece(self) -> None:
        """Бесплатный серийный экземпляр даёт две записи ±1 PCS в исходной валюте."""
        dims = replace(self.f.first.dimensions, serial_id=StockSerialIdVO(uuid4()))
        source = self.f.position(dimensions=dims, base_uom=UomCodeVO("PCS"))
        target = self.f.position(
            dimensions=replace(dims, location_id=self.f.second_location.id),
            base_uom=UomCodeVO("PCS"),
        )
        layer = self.m.receipt_layer(source, "1", "0", currency="USD")
        self.prepare(source, target, layer, "1")
        journal = self.create()
        self.assertEqual(
            [entry.quantity_delta.value for entry in journal.entries],
            [Decimal(-1), Decimal(1)],
        )
        for entry in journal.entries:
            self.assertEqual(entry.base_uom, UomCodeVO("PCS"))
            self.assertEqual(entry.cost_delta, MoneyVO(Decimal(0), CurrencyVO("USD")))
        self.assertEqual(self.restore(journal), journal)

    def test_registers_exact_cumulative_rounding_under_small_decimal_context(
        self,
    ) -> None:
        """Накопленная разница 0.5834 фиксируется с обоими знаками без повторного округления."""
        layer = self.m.receipt_layer(self.f.first, "12", "1", currency="USD").consume(
            QuantityVO(Decimal(1)), expected_version=0, updated_at=self.m.v.at
        )
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            self.prepare(self.f.first, self.f.second, layer, "7")
            journal = self.create()
            self.assertEqual(self.restore(journal), journal)
        self.assertEqual(
            [entry.cost_delta for entry in journal.entries],
            [
                MoneyVO(Decimal(amount), CurrencyVO("USD"))
                for amount in ("-0.5834", "0.5834")
            ],
        )

    def test_rejects_partial_coverage_of_a_balanced_posting(self) -> None:
        """Даже проверенная пара не создаёт журнал части многопарного Ledger."""
        dims = replace(self.f.first.dimensions, owner_id=StockOwnerIdVO(uuid4()))
        a = self.f.position(dimensions=dims)
        b = self.f.position(
            dimensions=replace(dims, location_id=self.f.second_location.id)
        )
        positions = (*self.positions, a.snapshot(), b.snapshot())
        posting = self.f.movement(
            identifier=self.posting.id,
            posted_at=self.posting.posted_at,
            positions=positions,
            entries=(
                *self.posting.entries,
                self.f.entry("-7", a),
                self.f.entry("7", b),
            ),
        )
        with self.assertRaises(ValuationPostingSourceError):
            self.create(posting=posting.snapshot(), positions=positions)

    def test_rejects_unrelated_posting_reversal_and_foreign_entry_pair(self) -> None:
        """Журнал связывается с обычным INTERNAL_MOVE и точными ID проведённой пары."""
        snapshot = self.posting.snapshot()
        with self.assertRaises(ValuationPostingSourceError):
            self.create(posting=replace(snapshot, id=self.f.posting().id))
        for posting in (
            self.f.posting().snapshot(),
            replace(snapshot, reversal_of_id=self.f.posting().id),
            replace(
                snapshot,
                entries=(
                    replace(snapshot.entries[0], id=StockLedgerEntryIdVO(uuid4())),
                    snapshot.entries[1],
                ),
            ),
        ):
            with (
                self.subTest(posting=posting),
                self.assertRaises(StockMovementValuationSourceError),
            ):
                self.create(posting=posting)

    def test_rebuilds_movement_even_if_changed_consumption_and_destination_agree(
        self,
    ) -> None:
        """Самосогласованные стоимостные снимки сверяются с реальным временем StockPosting."""
        changed = replace(
            self.consumption,
            movement=replace(
                self.movement, moved_at=self.movement.moved_at + timedelta(minutes=1)
            ),
        )
        target = self.m.destination(changed)
        with self.assertRaises(ValuationPostingSourceError):
            self.create(consumption=changed, destination=target.basis_snapshot())
        with self.assertRaises(InvalidPostingContextError):
            self.create(locations=(self.locations[0],))

    def test_revalidates_consumption_and_destination_basis(self) -> None:
        """Отклоняет изменённый переход, стоимость, валюту, количество и происхождение назначения."""
        with self.assertRaises(InvalidValuationLayerMovementConsumptionSnapshotError):
            self.create(consumption=replace(self.consumption, version_after=2))
        basis = self.target.basis_snapshot()
        for changes in (
            dict(cost_basis=replace(basis.cost_basis, quantity=QuantityVO(Decimal(6)))),
            dict(
                cost_basis=replace(
                    basis.cost_basis, total_cost=MoneyVO(Decimal(85), CurrencyVO("UAH"))
                )
            ),
            dict(
                cost_basis=replace(
                    basis.cost_basis, total_cost=MoneyVO(Decimal(84), CurrencyVO("USD"))
                )
            ),
            dict(
                transfer_origin=replace(
                    basis.transfer_origin, parent_layer_id=ValuationLayerIdVO(uuid4())
                )
            ),
            dict(
                transfer_origin=replace(
                    basis.transfer_origin,
                    outgoing_entry_id=StockLedgerEntryIdVO(uuid4()),
                )
            ),
            dict(
                transfer_origin=replace(
                    basis.transfer_origin,
                    receipt_source=replace(
                        self.source.source,
                        ledger_entry_id=StockLedgerEntryIdVO(uuid4()),
                    ),
                )
            ),
            dict(
                source=replace(
                    basis.source, ledger_entry_id=StockLedgerEntryIdVO(uuid4())
                )
            ),
            dict(source=replace(basis.source, position_id=StockPositionIdVO(uuid4()))),
            dict(received_at=basis.received_at + timedelta(seconds=1)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(destination=replace(basis, **changes))
        with self.assertRaises(ValuationPostingSourceError):
            self.create(destination=self.source.receipt_valuation_snapshot())

    def test_requires_consistent_registration_times(self) -> None:
        """Отклоняет создание назначения до потребления и журнал до появления слоя."""
        basis = self.target.basis_snapshot()
        with self.assertRaises(ValuationPostingTimeError):
            self.create(destination=replace(basis, created_at=self.movement.moved_at))
        for at in (
            basis.created_at - timedelta(seconds=1),
            self.at.replace(tzinfo=None),
        ):
            with self.subTest(at=at), self.assertRaises(ValuationPostingTimeError):
                self.create(posted_at=at)

    def test_requires_one_unique_binding_per_layer(self) -> None:
        """Отклоняет недостающие, чужие и дублирующиеся привязки."""
        target, source = self.bindings
        for bindings in (
            (target,),
            (replace(target, layer_id=ValuationLayerIdVO(uuid4())), source),
        ):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(entry_bindings=bindings)
        for bindings in (
            (target, target),
            (target, replace(source, entry_id=target.entry_id)),
        ):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(DuplicateValuationEntryError),
            ):
                self.create(entry_bindings=bindings)

    def test_restore_rejects_unbalanced_pair_and_changed_accounting_dimensions(
        self,
    ) -> None:
        """Восстановление самостоятельно проверяет состав, дельты и контекст."""
        journal = self.create()
        outgoing, incoming = journal.entries
        for changes in (
            dict(quantity_delta=StockDeltaVO(Decimal(8))),
            dict(
                quantity_delta=outgoing.quantity_delta, cost_delta=outgoing.cost_delta
            ),
            dict(cost_delta=MoneyVO(Decimal(83), CurrencyVO("UAH"))),
            dict(cost_delta=MoneyVO(Decimal(84), CurrencyVO("USD"))),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidValuationPostingValueError),
            ):
                self.restore(journal, entries=(outgoing, replace(incoming, **changes)))
        with self.assertRaises(InvalidValuationPostingValueError):
            self.restore(journal, entries=(outgoing,))

    def test_restore_rejects_duplicate_references_across_directions(self) -> None:
        """Разные стороны требуют отдельных ID записи, Ledger, позиции и слоя."""
        journal = self.create()
        outgoing, incoming = journal.entries
        for name in ("id", "ledger_entry_id", "position_id", "layer_id"):
            with (
                self.subTest(name=name),
                self.assertRaises(DuplicateValuationEntryError),
            ):
                self.restore(
                    journal,
                    entries=(
                        outgoing,
                        replace(incoming, **{name: getattr(outgoing, name)}),
                    ),
                )
