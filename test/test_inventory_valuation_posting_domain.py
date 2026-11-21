"""Полная регистрация первоначальной стоимости прихода без изменения запасов и слоёв."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_valuation_layer_domain as valuation_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.valuation_layer.value_object.cost_basis import (
    CostBasisVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.source import (
    ValuationLayerSourceVO,
)
from src.modules.inventory.domain.valuation_posting.aggregate import ValuationPosting
from src.modules.inventory.domain.valuation_posting.entity.valuation_entry import (
    ValuationEntry,
)
from src.modules.inventory.domain.valuation_posting.error import (
    DuplicateValuationEntryError,
    InvalidValuationEntryBindingError,
    InvalidValuationEntryError,
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
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class ValuationPostingDomainTests(unittest.TestCase):
    """Проверяет границы агрегата, полноту оснований и неизменность стоимостного журнала."""

    def setUp(self) -> None:
        """Готовит физический приход пяти KG и слой первоначальной стоимости 250 UAH."""
        self.v = valuation_fixture.ValuationLayerDomainTests()
        self.v.setUp()
        self.f = self.v.f
        self.stock = self.v.posting
        self.layer = self.v.create()
        self.snapshot = self.layer.receipt_valuation_snapshot()
        self.binding = ValuationEntryBindingVO(
            self.layer.id, ValuationEntryIdVO(uuid4())
        )
        self.at = self.layer.created_at + timedelta(hours=1)

    def create(self, **changes: object) -> ValuationPosting:
        """Строит полную оценку прихода по снимкам и явно назначенным ID записей."""
        return ValuationPosting.create_from_receipt(
            **(
                dict(
                    identifier=ValuationPostingIdVO(uuid4()),
                    posting=self.stock.snapshot(),
                    layers=(self.snapshot,),
                    entry_bindings=(self.binding,),
                    positions=(self.f.first.snapshot(),),
                    locations=(self.f.first_location,),
                    posted_at=self.at,
                )
                | changes
            )
        )

    def restore(self, posting: ValuationPosting, **changes: object) -> ValuationPosting:
        """Передаёт весь собственный состав восстановления без внешних оснований."""
        values = {field.name: getattr(posting, field.name) for field in fields(posting)}
        values["identifier"] = values.pop("id")
        return ValuationPosting.restore(**(values | changes))

    def restore_entry(self, entry: ValuationEntry, **changes: object) -> ValuationEntry:
        """Восстанавливает дочернюю запись с полным набором её собственных полей."""
        values = {field.name: getattr(entry, field.name) for field in fields(entry)}
        values["identifier"] = values.pop("id")
        return ValuationEntry.restore(**(values | changes))

    def multiple_context(self) -> dict[str, object]:
        """Готовит две записи разных товаров, единиц, владельцев, складов и валют."""
        second_location = replace(
            self.f.second_location, warehouse_id=WarehouseIdVO(uuid4())
        )
        second = self.f.position(
            dimensions=replace(
                self.f.dimensions,
                location_id=second_location.id,
                inventory_item_id=InventoryItemIdVO(uuid4()),
                owner_id=StockOwnerIdVO(uuid4()),
            ),
            base_uom=UomCodeVO("PCS"),
        )
        positions = (self.f.first.snapshot(), second.snapshot())
        locations = (self.f.first_location, second_location)
        stock = self.f.posting(
            entries=(self.f.entry("5"), self.f.entry("12", second)), positions=positions
        )
        layers = tuple(
            self.v.create(
                receipt=stock.receipt_valuation_snapshot(
                    ledger_entry_id=entry.id, position=position, location=location
                ),
                total_cost=MoneyVO(Decimal(cost), CurrencyVO(currency)),
            ).receipt_valuation_snapshot()
            for entry, position, location, cost, currency in zip(
                stock.entries,
                positions,
                locations,
                ("250", "60"),
                ("UAH", "USD"),
            )
        )
        return dict(
            posting=stock.snapshot(),
            layers=layers,
            positions=positions,
            locations=locations,
            entry_bindings=tuple(
                ValuationEntryBindingVO(layer.id, ValuationEntryIdVO(uuid4()))
                for layer in layers
            ),
        )

    def malformed_money(self, amount: object) -> MoneyVO:
        """Обходит конструктор для проверки защиты от повреждённого сохранённого MoneyVO."""
        money = object.__new__(MoneyVO)
        object.__setattr__(money, "amount", amount)
        object.__setattr__(money, "currency", CurrencyVO("UAH"))
        return money

    def test_create_derives_complete_entry_and_original_times(self) -> None:
        """Корень и запись получают все значения из проверенных источников и явной привязки ID."""
        posting = self.create()
        self.assertEqual(posting.stock_posting_id, self.stock.id)
        self.assertIs(posting.operation_type, StockOperationType.RECEIPT)
        self.assertEqual(posting.stock_posted_at, self.stock.posted_at)
        self.assertEqual(posting.posted_at, self.at)
        (entry,) = posting.entries
        self.assertEqual(entry.id, self.binding.entry_id)
        self.assertEqual(entry.layer_id, self.layer.id)
        self.assertEqual(entry.ledger_entry_id, self.stock.entries[0].id)
        self.assertEqual(entry.position_id, self.f.first.id)
        self.assertEqual(entry.inventory_item_id, self.layer.inventory_item_id)
        self.assertEqual(entry.owner_id, self.layer.owner_id)
        self.assertEqual(entry.warehouse_id, self.layer.warehouse_id)
        self.assertEqual(entry.base_uom, self.layer.base_uom)
        self.assertEqual(entry.quantity_delta, StockDeltaVO(Decimal(5)))
        self.assertIs(entry.cost_delta, self.layer.cost_basis.total_cost)

    def test_multiple_entries_preserve_dimensions_units_and_currencies(self) -> None:
        """Разные единицы и валюты сохраняются по записям без некорректного общего итога."""
        context = self.multiple_context()
        posting = self.create(**context)
        first, second = posting.entries
        self.assertEqual((first.base_uom.value, second.base_uom.value), ("KG", "PCS"))
        self.assertEqual(
            (first.cost_delta.currency, second.cost_delta.currency),
            (CurrencyVO("UAH"), CurrencyVO("USD")),
        )
        self.assertEqual(
            (first.cost_delta.amount, second.cost_delta.amount),
            (Decimal(250), Decimal(60)),
        )
        self.assertNotEqual(first.inventory_item_id, second.inventory_item_id)
        self.assertNotEqual(first.owner_id, second.owner_id)
        self.assertNotEqual(first.warehouse_id, second.warehouse_id)

    def test_order_follows_ledger_independently_of_context_order(self) -> None:
        """Перестановка слоёв, привязок и снимков не меняет соответствие и порядок записей журнала."""
        context = self.multiple_context()
        expected = self.create(**context)
        for key in ("layers", "entry_bindings", "positions", "locations"):
            context[key] = tuple(reversed(context[key]))
        result = self.create(**context)
        self.assertEqual(result.entries, expected.entries)

    def test_layer_snapshot_preserves_original_basis_after_partial_and_full_consumption(
        self,
    ) -> None:
        """Снимок первоначального прихода не зависит от изменяющихся остатков и версии слоя."""
        for quantity in ("2", "5"):
            consumed = self.layer.consume(
                QuantityVO(Decimal(quantity)), expected_version=0, updated_at=self.at
            )
            snapshot = consumed.receipt_valuation_snapshot()
            self.assertEqual(snapshot, self.snapshot)
            posting = self.create(layers=(snapshot,))
            self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(5))
            self.assertEqual(posting.entries[0].cost_delta.amount, Decimal(250))
            self.assertEqual(consumed.version, 1)

    def test_zero_cost_receipt_still_creates_valuation_entry(self) -> None:
        """Бесплатный приход имеет полную положительную запись количества с нулевой стоимостью."""
        layer = self.v.create(total_cost=MoneyVO(Decimal(0), CurrencyVO("EUR")))
        posting = self.create(
            layers=(layer.receipt_valuation_snapshot(),),
            entry_bindings=(ValuationEntryBindingVO(layer.id, self.binding.entry_id),),
        )
        self.assertEqual(
            posting.entries[0].cost_delta, MoneyVO(Decimal(0), CurrencyVO("EUR"))
        )
        self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(5))

    def test_create_does_not_mutate_source_layer_posting_or_physical_balance(
        self,
    ) -> None:
        """Регистрация стоимости не потребляет слой, не применяет Ledger и не меняет физический запас."""
        layer_before = self.v.restore(self.layer)
        stock_before = self.stock.snapshot()
        qty_before = self.f.first.on_hand_qty
        self.create()
        self.assertEqual(self.layer, layer_before)
        self.assertEqual(self.stock.snapshot(), stock_before)
        self.assertEqual(self.f.first.on_hand_qty, qty_before)
        self.assertEqual(self.f.first.version, 0)

    def test_posting_entries_and_snapshot_are_frozen(self) -> None:
        """Неизменяемые факт, дочерняя запись и снимок не предоставляют прямого редактирования."""
        posting = self.create()
        for obj, name, value in (
            (posting, "posted_at", self.at),
            (posting.entries[0], "cost_delta", self.v.cost),
            (self.snapshot, "created_at", self.at),
        ):
            with self.subTest(obj=type(obj)), self.assertRaises(FrozenInstanceError):
                setattr(obj, name, value)

    def test_empty_or_incomplete_layer_coverage_is_rejected(self) -> None:
        """Нельзя зарегистрировать пустую оценку или только часть записей физического прихода."""
        context = self.multiple_context()
        for layers in ((), context["layers"][:1]):
            with (
                self.subTest(layers=layers),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(**(context | dict(layers=layers)))

    def test_extra_layer_from_unknown_ledger_entry_is_rejected(self) -> None:
        """Лишняя запись слоя не считается частью выбранного физического прихода."""
        layer = replace(
            self.snapshot,
            id=ValuationLayerIdVO(uuid4()),
            source=replace(
                self.snapshot.source, ledger_entry_id=StockLedgerEntryIdVO(uuid4())
            ),
        )
        with self.assertRaises(ValuationPostingSourceError):
            self.create(layers=(self.snapshot, layer))

    def test_duplicate_layer_identity_or_ledger_entry_is_rejected(self) -> None:
        """Повтор ID слоя или два слоя одной записи Ledger отклоняются до построения записей."""
        context = self.multiple_context()
        a, b = context["layers"]
        for layers in ((a, replace(b, id=a.id)), (a, replace(a, id=b.id))):
            with (
                self.subTest(layers=layers),
                self.assertRaises(DuplicateValuationEntryError),
            ):
                self.create(**(context | dict(layers=layers)))

    def test_missing_or_extra_binding_is_rejected(self) -> None:
        """Каждому слою нужен ровно один явно назначенный ID записи стоимости."""
        extra = ValuationEntryBindingVO(
            ValuationLayerIdVO(uuid4()), ValuationEntryIdVO(uuid4())
        )
        for bindings in ((), (extra,), (self.binding, extra)):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(entry_bindings=bindings)

    def test_duplicate_binding_layer_or_entry_id_is_rejected(self) -> None:
        """Ни слой, ни ID стоимостной записи нельзя назначить дважды."""
        context = self.multiple_context()
        a, b = context["entry_bindings"]
        for bindings in (
            (a, replace(b, entry_id=a.entry_id)),
            (a, replace(b, layer_id=a.layer_id)),
        ):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(DuplicateValuationEntryError),
            ):
                self.create(**(context | dict(entry_bindings=bindings)))

    def test_layer_source_must_match_posting_ledger_and_position(self) -> None:
        """Все три ссылки исходного слоя проверяются, а не только совпадение количества."""
        for changes in (
            dict(posting_id=StockPostingIdVO(uuid4())),
            dict(ledger_entry_id=StockLedgerEntryIdVO(uuid4())),
            dict(position_id=StockPositionIdVO(uuid4())),
        ):
            layer = replace(
                self.snapshot, source=replace(self.snapshot.source, **changes)
            )
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(layers=(layer,))

    def test_layer_dimensions_quantity_and_receipt_time_must_match(self) -> None:
        """Одинаковые ссылки не скрывают иной товар, владельца, склад, единицу, количество или время."""
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
            dict(cost_basis=CostBasisVO(QuantityVO(Decimal(6)), self.v.cost)),
            dict(received_at=self.snapshot.received_at + timedelta(seconds=1)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(layers=(replace(self.snapshot, **changes),))

    def test_rejects_nonreceipt_operations_and_reversal_of_issue(self) -> None:
        """Перемещение, корректировка и положительная компенсация расхода не создают закупочную оценку."""
        issue = self.f.posting(
            operation_type=StockOperationType.ISSUE, entries=(self.f.entry("-5"),)
        )
        adjustment = replace(
            self.stock.snapshot(), operation_type=StockOperationType.ADJUSTMENT
        )
        for stock in (
            issue.snapshot(),
            self.f.movement().snapshot(),
            adjustment,
            self.f.reverse(issue).snapshot(),
        ):
            with (
                self.subTest(operation=stock.operation_type),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(posting=stock)

    def test_rejects_raw_aggregates_collections_and_wrong_snapshot_types(self) -> None:
        """Публичная фабрика требует специализированные снимки и неизменяемые tuple."""
        for changes in (
            dict(posting=self.stock),
            dict(posting=None),
            dict(layers=[self.snapshot]),
            dict(layers=(self.layer,)),
            dict(layers=(None,)),
            dict(entry_bindings=[self.binding]),
            dict(entry_bindings=(None,)),
            dict(positions=[self.f.first.snapshot()]),
            dict(locations=[self.f.first_location]),
            dict(locations=(None,)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.create(**changes)

    def test_positions_require_exact_coverage_and_matching_unit(self) -> None:
        """Проверка исходных позиций не допускает пропусков, повторов, лишних ссылок и иной базовой единицы."""
        position = self.f.first.snapshot()
        for positions in (
            (),
            (position, position),
            (position, self.f.second.snapshot()),
            (replace(position, base_uom=UomCodeVO("G")),),
        ):
            with self.subTest(positions=positions), self.assertRaises(InventoryError):
                self.create(positions=positions)

    def test_locations_require_exact_unique_coverage(self) -> None:
        """Для всех исходных позиций требуется ровно по одному снимку используемой локации."""
        location = self.f.first_location
        for locations in (
            (),
            (location, location),
            (location, self.f.second_location),
            (self.f.second_location,),
        ):
            with (
                self.subTest(locations=locations),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(locations=locations)

    def test_shared_location_can_serve_multiple_positions(self) -> None:
        """Несколько разных товаров в одном адресе используют один снимок локации."""
        context = self.multiple_context()
        first, second = context["positions"]
        shared_second = replace(
            second,
            dimensions=replace(second.dimensions, location_id=self.f.first_location.id),
        )
        layers = context["layers"]
        context.update(
            positions=(first, shared_second),
            locations=(self.f.first_location,),
            layers=(layers[0], replace(layers[1], warehouse_id=self.f.warehouse.id)),
        )
        self.assertEqual(len(self.create(**context).entries), 2)

    def test_inactive_location_does_not_invalidate_historical_valuation(self) -> None:
        """Текущее отключение локации не меняет первоначальное основание уже проведённого прихода."""
        posting = self.create(
            locations=(replace(self.f.first_location, is_active=False),)
        )
        self.assertEqual(
            posting.entries[0].cost_delta, self.layer.cost_basis.total_cost
        )

    def test_lot_and_serial_receipts_reuse_existing_source_rules(self) -> None:
        """Стоимость партии и серийного экземпляра выводится через прежнюю проверку источника прихода."""
        for serial in (False, True):
            position = self.f.position(
                dimensions=replace(
                    self.f.dimensions,
                    lot_id=StockLotIdVO(uuid4()),
                    serial_id=StockSerialIdVO(uuid4()) if serial else None,
                ),
                base_uom=UomCodeVO("PCS") if serial else UomCodeVO("KG"),
            )
            stock = self.f.posting(
                entries=(self.f.entry("1", position),), positions=(position.snapshot(),)
            )
            receipt = stock.receipt_valuation_snapshot(
                ledger_entry_id=stock.entries[0].id,
                position=position.snapshot(),
                location=self.f.first_location,
            )
            layer = self.v.create(receipt=receipt)
            posting = self.create(
                posting=stock.snapshot(),
                layers=(layer.receipt_valuation_snapshot(),),
                positions=(position.snapshot(),),
                entry_bindings=(
                    ValuationEntryBindingVO(layer.id, self.binding.entry_id),
                ),
            )
            self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(1))

    def test_serial_receipt_cannot_hide_multiple_units(self) -> None:
        """Повторная проверка источника запрещает оценить несколько штук одного серийного экземпляра."""
        position = self.f.position(
            dimensions=replace(self.f.dimensions, serial_id=StockSerialIdVO(uuid4())),
            base_uom=UomCodeVO("PCS"),
        )
        stock = self.v.historical_posting(self.f.entry("2", position))
        layer = replace(
            self.snapshot,
            source=ValuationLayerSourceVO(stock.id, stock.entries[0].id, position.id),
            base_uom=UomCodeVO("PCS"),
            cost_basis=CostBasisVO(QuantityVO(Decimal(2)), self.v.cost),
        )
        with self.assertRaises(InventoryError):
            self.create(
                posting=stock.snapshot(),
                layers=(layer,),
                positions=(position.snapshot(),),
            )

    def test_historical_conversion_is_preserved_without_current_recalculation(
        self,
    ) -> None:
        """Исторический коэффициент прихода не заменяется современным при регистрации стоимости."""
        conversion = QuantityConversionSnapshotVO(
            QuantityVO(Decimal(1000)), UomCodeVO("G"), Decimal(".002")
        )
        entry = replace(
            self.stock.entries[0],
            quantity_delta=StockDeltaVO(Decimal(2)),
            conversion=conversion,
        )
        stock = self.v.historical_posting(entry)
        layer = self.v.create(receipt=self.v.produce(stock))
        posting = self.create(
            posting=stock.snapshot(),
            layers=(layer.receipt_valuation_snapshot(),),
            entry_bindings=(ValuationEntryBindingVO(layer.id, self.binding.entry_id),),
        )
        self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(2))

    def test_registration_time_is_normalized_and_can_equal_layer_creation(self) -> None:
        """Стоимость может регистрироваться в момент создания слоя; aware-смещение нормализуется в UTC."""
        posting = self.create(
            posted_at=self.layer.created_at.astimezone(timezone(timedelta(hours=2)))
        )
        self.assertEqual(posting.posted_at, self.layer.created_at)
        self.assertEqual(posting.posted_at.utcoffset(), timedelta(0))

    def test_registration_cannot_precede_receipt_or_layer_creation(self) -> None:
        """Физическое проведение и создание каждого слоя предшествуют регистрации стоимости."""
        for at in (
            self.stock.posted_at - timedelta(seconds=1),
            self.layer.created_at - timedelta(microseconds=1),
        ):
            with self.subTest(at=at), self.assertRaises(ValuationPostingTimeError):
                self.create(posted_at=at)

    def test_registration_requires_explicit_aware_datetime(self) -> None:
        """Фабрика не читает часы и не принимает наивные или сырые значения времени."""
        for at in (None, "now", self.at.replace(tzinfo=None)):
            with self.subTest(at=at), self.assertRaises(ValuationPostingTimeError):
                self.create(posted_at=at)

    def test_restore_preserves_all_fields_without_external_context(self) -> None:
        """Восстановление сохраняет собственную историю, не требуя снимков исходного прихода и слоёв."""
        posting = self.create(**self.multiple_context())
        restored = self.restore(posting)
        self.assertEqual(restored, posting)
        self.assertIs(restored.entries, posting.entries)
        for entry in posting.entries:
            self.assertEqual(self.restore_entry(entry), entry)

    def test_restore_normalizes_both_aware_times(self) -> None:
        """Обе сохранённые даты восстановления нормализуются в UTC с сохранением момента."""
        posting = self.create()
        zone = timezone(timedelta(hours=-5))
        restored = self.restore(
            posting,
            stock_posted_at=posting.stock_posted_at.astimezone(zone),
            posted_at=posting.posted_at.astimezone(zone),
        )
        self.assertEqual(restored, posting)

    def test_restore_requires_nominal_ids_compatible_operation_and_nonempty_tuple(
        self,
    ) -> None:
        """Аннотации не заменяют проверки ID, вида операции и состава дочерних записей."""
        posting = self.create()
        for changes in (
            dict(identifier=uuid4()),
            dict(stock_posting_id=uuid4()),
            dict(operation_type="RECEIPT"),
            dict(operation_type=StockOperationType.ISSUE),
            dict(entries=()),
            dict(entries=list(posting.entries)),
            dict(entries=(None,)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidValuationPostingValueError),
            ):
                self.restore(posting, **changes)

    def test_restore_rejects_duplicate_entry_ledger_layer_and_position(self) -> None:
        """Собственные инварианты уникальности проверяются без повторного чтения Ledger."""
        posting = self.create(**self.multiple_context())
        a, b = posting.entries
        for name in ("id", "ledger_entry_id", "layer_id", "position_id"):
            duplicate = replace(b, **{name: getattr(a, name)})
            with (
                self.subTest(name=name),
                self.assertRaises(DuplicateValuationEntryError),
            ):
                self.restore(posting, entries=(a, duplicate))

    def test_restore_rejects_naive_and_inverted_times(self) -> None:
        """Сохранённая регистрация не может предшествовать физическому проведению."""
        posting = self.create()
        for changes in (
            dict(stock_posted_at=None),
            dict(posted_at=self.at.replace(tzinfo=None)),
            dict(posted_at=posting.stock_posted_at - timedelta(seconds=1)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationPostingTimeError),
            ):
                self.restore(posting, **changes)

    def test_entry_restore_rejects_wrong_nominal_fields(self) -> None:
        """Дочерняя Entity проверяет собственные типы каждой ссылки и значения."""
        entry = self.create().entries[0]
        for name in (
            "identifier",
            "ledger_entry_id",
            "position_id",
            "layer_id",
            "inventory_item_id",
            "owner_id",
            "warehouse_id",
            "base_uom",
            "quantity_delta",
            "cost_delta",
        ):
            with self.subTest(name=name), self.assertRaises(InvalidValuationEntryError):
                self.restore_entry(entry, **{name: None})

    def test_entry_restore_rejects_zero_opposite_and_corrupted_quantity(self) -> None:
        """Ноль, неконечное количество и отрицательное направление при положительной стоимости отклоняются."""
        entry = self.create().entries[0]
        for value in (
            Decimal(0),
            Decimal(-1),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            "1",
        ):
            delta = object.__new__(StockDeltaVO)
            object.__setattr__(delta, "value", value)
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidValuationEntryError),
            ):
                self.restore_entry(entry, quantity_delta=delta)

    def test_entry_restore_rejects_opposite_nonfinite_and_noncanonical_cost(
        self,
    ) -> None:
        """Стоимость согласована с положительным количеством и соответствует сохранённой точности MoneyVO."""
        entry = self.create().entries[0]
        for value in (
            Decimal(-1),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            Decimal("1.00001"),
            "1",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidValuationEntryError),
            ):
                self.restore_entry(entry, cost_delta=self.malformed_money(value))

    def test_restore_revalidates_corrupted_child_entity(self) -> None:
        """Прямой вызов конструктора дочерней записи не обходит проверки агрегата."""
        posting = self.create()
        child = replace(posting.entries[0], quantity_delta=StockDeltaVO(Decimal(0)))
        with self.assertRaises(InvalidValuationEntryError):
            self.restore(posting, entries=(child,))

    def test_binding_requires_nominal_layer_and_entry_identifiers(self) -> None:
        """Сырые UUID и идентификаторы других сущностей не заменяют явную привязку."""
        for layer_id, entry_id in (
            (uuid4(), self.binding.entry_id),
            (self.layer.id, uuid4()),
            (self.layer.id, StockLedgerEntryIdVO(uuid4())),
        ):
            with (
                self.subTest(layer_id=layer_id, entry_id=entry_id),
                self.assertRaises(InvalidValuationEntryBindingError),
            ):
                ValuationEntryBindingVO(layer_id, entry_id)
        for cls in (ValuationEntryIdVO, ValuationPostingIdVO):
            with self.assertRaises(EntityIdTypeError):
                cls("raw")

    def test_policy_revalidates_corrupted_binding(self) -> None:
        """Повреждённая после обхода фабрики привязка повторно проверяется перед построением журнала."""
        binding = object.__new__(ValuationEntryBindingVO)
        object.__setattr__(binding, "layer_id", self.layer.id)
        object.__setattr__(binding, "entry_id", uuid4())
        with self.assertRaises(InvalidValuationEntryBindingError):
            self.create(entry_bindings=(binding,))

    def test_layer_snapshot_validates_all_own_types(self) -> None:
        """Снимок первоначальной стоимости требует номинальные поля и корректный CostBasisVO."""
        for name in (
            "id",
            "source",
            "inventory_item_id",
            "owner_id",
            "warehouse_id",
            "base_uom",
            "cost_basis",
        ):
            with self.subTest(name=name), self.assertRaises(InventoryError):
                replace(self.snapshot, **{name: None}).ensure_valid()

    def test_layer_snapshot_requires_saved_utc_chronology(self) -> None:
        """Готовый снимок хранит UTC-даты регистрации не раньше исходного прихода."""
        for changes in (
            dict(received_at=None),
            dict(created_at=self.at.replace(tzinfo=None)),
            dict(created_at=self.snapshot.received_at - timedelta(seconds=1)),
            dict(
                received_at=self.snapshot.received_at.astimezone(
                    timezone(timedelta(hours=2))
                )
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.create(layers=(replace(self.snapshot, **changes),))

    def test_snapshot_producer_revalidates_layer_before_export(self) -> None:
        """Некорректный остаток собственного слоя не может экспортировать внешне корректное основание."""
        broken = replace(
            self.layer, remaining_cost=MoneyVO(Decimal(0), CurrencyVO("UAH"))
        )
        with self.assertRaises(InventoryError):
            broken.receipt_valuation_snapshot()

    def test_small_decimal_context_preserves_quantity_and_full_cost(self) -> None:
        """Построение и восстановление не округляют историческое количество и первоначальную сумму."""
        stock = self.f.posting(entries=(self.f.entry("123.456789"),))
        layer = self.v.create(
            receipt=self.v.produce(stock),
            total_cost=MoneyVO(Decimal("9876.5432"), CurrencyVO("EUR")),
        )
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            posting = self.create(
                posting=stock.snapshot(),
                layers=(layer.receipt_valuation_snapshot(),),
                entry_bindings=(
                    ValuationEntryBindingVO(layer.id, self.binding.entry_id),
                ),
            )
            restored = self.restore(posting)
        self.assertEqual(
            restored.entries[0].quantity_delta.value, Decimal("123.456789")
        )
        self.assertEqual(restored.entries[0].cost_delta.amount, Decimal("9876.5432"))

    def test_repeated_domain_creation_does_not_claim_global_idempotency(self) -> None:
        """Одинаковое основание может построить второй объект: однократность между фактами обеспечит хранение."""
        a, b = self.create(), self.create()
        self.assertNotEqual(a.id, b.id)
        self.assertEqual(a.stock_posting_id, b.stock_posting_id)
        self.assertEqual(a.entries, b.entries)


if __name__ == "__main__":
    unittest.main()
