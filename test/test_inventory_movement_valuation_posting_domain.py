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
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
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
from src.modules.inventory.domain.valuation_posting.movement_pair_snapshot import (
    ValuationMovementPairSnapshot,
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
                    movement_pairs=journal.movement_pairs,
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


class MultipleMovementValuationPairsDomainTests(unittest.TestCase):
    """Проверяет многопарную регистрацию и восстановление явных связей Ledger."""

    def setUp(self) -> None:
        """Готовит две пары одного товара по 7 KG с разной стоимостью."""
        self.single = MovementValuationPostingDomainTests()
        self.single.setUp()
        self.prepare_pairs()

    def prepare_pairs(self, *, second_currency: str = "UAH") -> None:
        """Добавляет второе движение между другими адресами того же склада."""
        one = self.single
        f = one.f
        source_location = replace(f.first_location, id=StockLocationIdVO(uuid4()))
        target_location = replace(f.second_location, id=StockLocationIdVO(uuid4()))
        source = f.position(
            dimensions=replace(f.dimensions, location_id=source_location.id)
        )
        target = f.position(
            dimensions=replace(f.dimensions, location_id=target_location.id)
        )
        self.positions = (*one.positions, source.snapshot(), target.snapshot())
        self.locations = (*one.locations, source_location, target_location)
        outgoing = f.entry("-7", source)
        incoming = f.entry("7", target)
        self.posting = f.movement(
            identifier=one.posting.id,
            entries=(outgoing, *one.posting.entries, incoming),
            positions=self.positions,
            locations=self.locations,
            posted_at=one.posting.posted_at,
        )
        receipt = f.posting(
            entries=(f.entry("7", source),), positions=(source.snapshot(),)
        )
        layer = ValuationLayer.create_from_receipt(
            identifier=ValuationLayerIdVO(uuid4()),
            receipt=receipt.receipt_valuation_snapshot(
                ledger_entry_id=receipt.entries[0].id,
                position=source.snapshot(),
                location=source_location,
            ),
            total_cost=MoneyVO(Decimal(105), CurrencyVO(second_currency)),
            created_at=receipt.posted_at,
        )
        movement = self.posting.movement_valuation_snapshot(
            pair=StockMovementEntryPairVO(outgoing.id, incoming.id),
            positions=self.positions,
            locations=self.locations,
        )
        _, consumption = one.m.consume(layer, movement)
        destination = one.m.destination(consumption)
        self.pairs = (
            ValuationMovementPairSnapshot(one.consumption, one.target.basis_snapshot()),
            ValuationMovementPairSnapshot(consumption, destination.basis_snapshot()),
        )
        self.bindings = (
            *one.bindings,
            ValuationEntryBindingVO(destination.id, ValuationEntryIdVO(uuid4())),
            ValuationEntryBindingVO(layer.id, ValuationEntryIdVO(uuid4())),
        )

    def create(self, **changes: object) -> ValuationPosting:
        """Создаёт один журнал всего физического проведения."""
        return ValuationPosting.create_from_movement_pairs(
            **(
                dict(
                    identifier=self.single.identifier,
                    posting=self.posting.snapshot(),
                    pairs=self.pairs,
                    entry_bindings=self.bindings,
                    positions=self.positions,
                    locations=self.locations,
                    posted_at=self.single.at,
                )
                | changes
            )
        )

    def test_registers_both_pairs_with_original_sources_and_destinations(self) -> None:
        """Равные количества разных пар сохраняют собственную стоимость и явную связь."""
        journal = self.create()
        self.assertEqual(journal.stock_posting_id, self.posting.id)
        self.assertEqual(
            journal.movement_pairs,
            tuple(p.consumption.movement.pair for p in self.pairs),
        )
        self.assertEqual(
            [
                (entry.quantity_delta.value, entry.cost_delta.amount)
                for entry in journal.entries
            ],
            [
                (Decimal(qty), Decimal(cost))
                for qty, cost in ((-7, -84), (7, 84), (-7, -105), (7, 105))
            ],
        )
        self.assertEqual(
            [entry.layer_id for entry in journal.entries],
            [
                layer_id
                for pair in self.pairs
                for layer_id in (pair.consumption.layer.id, pair.destination.id)
            ],
        )
        self.assertEqual(self.single.restore(journal), journal)
        reversed_pairs = self.create(pairs=self.pairs[::-1])
        self.assertEqual(reversed_pairs.movement_pairs, journal.movement_pairs[::-1])
        self.assertEqual(
            reversed_pairs.entries, (*journal.entries[2:], *journal.entries[:2])
        )

    def test_allows_independent_currencies_for_different_pairs(self) -> None:
        """Каждая пара погашается в своей валюте при общем физическом проведении."""
        self.prepare_pairs(second_currency="USD")
        journal = self.create()
        self.assertEqual(
            [entry.cost_delta.currency for entry in journal.entries],
            [
                CurrencyVO("UAH"),
                CurrencyVO("UAH"),
                CurrencyVO("USD"),
                CurrencyVO("USD"),
            ],
        )
        self.assertEqual(self.single.restore(journal), journal)

    def test_single_pair_factory_and_legacy_restore_remain_compatible(self) -> None:
        """Старая фабрика и запись без сохранённой связи приводятся к тому же основанию."""
        one = self.single
        journal = one.create()
        self.assertEqual(
            self.create(
                posting=one.posting.snapshot(),
                pairs=self.pairs[:1],
                entry_bindings=one.bindings,
                positions=one.positions,
                locations=one.locations,
            ),
            journal,
        )
        restored = one.restore(
            journal, movement_pairs=None, entries=journal.entries[::-1]
        )
        self.assertEqual(restored.movement_pairs, journal.movement_pairs)
        self.assertEqual(restored.entries, journal.entries[::-1])

    def test_rejects_incomplete_and_repeated_physical_pairs(self) -> None:
        """Для полного журнала нужны все Ledger ID, каждый ровно один раз."""
        for pairs in ((), self.pairs[:1], [*self.pairs], (None, *self.pairs)):
            with (
                self.subTest(pairs=pairs),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(pairs=pairs)
        with self.assertRaises(DuplicateValuationEntryError):
            self.create(pairs=(*self.pairs, self.pairs[0]))

    def test_rejects_crossed_destinations_and_reused_layer_id(self) -> None:
        """Совпадение количества не разрешает подменить основание или повторно использовать слой."""
        first, second = self.pairs
        with self.assertRaises(ValuationPostingSourceError):
            self.create(pairs=(replace(first, destination=second.destination), second))
        duplicate_layer = replace(second.destination, id=first.destination.id)
        with self.assertRaises(DuplicateValuationEntryError):
            self.create(pairs=(first, replace(second, destination=duplicate_layer)))

    def test_requires_bindings_and_chronology_for_every_pair(self) -> None:
        """Правильная первая пара не скрывает отсутствующую привязку или позднее назначение второй."""
        with self.assertRaises(ValuationPostingSourceError):
            self.create(entry_bindings=self.bindings[:-1])
        first, second = self.pairs
        late = replace(
            second.destination, created_at=self.single.at + timedelta(seconds=1)
        )
        with self.assertRaises(ValuationPostingTimeError):
            self.create(pairs=(first, replace(second, destination=late)))

    def test_restore_requires_complete_explicit_and_directional_pairs(self) -> None:
        """Восстановление требует типизированных связей со всеми сторонами Ledger."""
        journal = self.create()
        first, second = journal.movement_pairs
        for pairs in (
            None,
            (),
            (first,),
            (first, None),
            (first, replace(second, incoming_entry_id=StockLedgerEntryIdVO(uuid4()))),
            (
                first,
                StockMovementEntryPairVO(
                    second.incoming_entry_id, second.outgoing_entry_id
                ),
            ),
        ):
            with (
                self.subTest(pairs=pairs),
                self.assertRaises(InvalidValuationPostingValueError),
            ):
                self.single.restore(journal, movement_pairs=pairs)
        with self.assertRaises(DuplicateValuationEntryError):
            self.single.restore(journal, movement_pairs=(first, second, first))
        with self.assertRaises(InvalidValuationPostingValueError):
            self.single.restore(
                journal,
                operation_type=StockOperationType.ISSUE,
                entries=(journal.entries[0],),
            )

    def test_restore_rejects_pair_imbalance_even_if_grand_total_is_zero(self) -> None:
        """Встречные суммы должны совпасть по сохранённым связям, а не только по журналу."""
        journal = self.create()
        first, second = journal.movement_pairs
        crossed = (
            replace(first, incoming_entry_id=second.incoming_entry_id),
            replace(second, incoming_entry_id=first.incoming_entry_id),
        )
        with self.assertRaises(InvalidValuationPostingValueError):
            self.single.restore(journal, movement_pairs=crossed)

    def test_restore_rejects_two_balanced_pairs_in_different_warehouses(self) -> None:
        """Две самостоятельные сбалансированные пары должны принадлежать одному складу."""
        journal = self.create()
        warehouse_id = WarehouseIdVO(uuid4())
        entries = (
            *journal.entries[:2],
            *(
                replace(entry, warehouse_id=warehouse_id)
                for entry in journal.entries[2:]
            ),
        )
        with self.assertRaises(InvalidValuationPostingValueError):
            self.single.restore(journal, entries=entries)
