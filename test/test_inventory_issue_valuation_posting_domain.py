"""Полная расходная регистрация стоимости по проверенным результатам потребления слоёв."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_issue_valuation_domain as issue_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
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
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerConsumptionSnapshotError,
)
from src.modules.inventory.domain.valuation_posting.aggregate import ValuationPosting
from src.modules.inventory.domain.valuation_posting.entity.valuation_entry import (
    ValuationEntry,
)
from src.modules.inventory.domain.valuation_posting.error import (
    DuplicateValuationEntryError,
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
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class IssueValuationPostingDomainTests(unittest.TestCase):
    """Проверяет полное соответствие расхода и потребления, знаки, историю и границы агрегатов."""

    def setUp(self) -> None:
        """Готовит ISSUE двух KG и потребление 100 UAH из слоя пяти KG за 250 UAH."""
        self.fx = issue_fixture.IssueValuationDomainTests()
        self.fx.setUp()
        self.changed, self.consumption = self.fx.consume()
        self.binding = ValuationEntryBindingVO(
            self.fx.layer.id, ValuationEntryIdVO(uuid4())
        )
        self.at = self.fx.at + timedelta(hours=1)

    def create(self, **changes: object) -> ValuationPosting:
        """Регистрирует весь физический ISSUE по историческим результатам и явным ID записей."""
        return ValuationPosting.create_from_issue(
            **(
                dict(
                    identifier=ValuationPostingIdVO(uuid4()),
                    posting=self.fx.posting.snapshot(),
                    consumptions=(self.consumption,),
                    entry_bindings=(self.binding,),
                    positions=(self.fx.f.first.snapshot(),),
                    locations=(self.fx.f.first_location,),
                    posted_at=self.at,
                )
                | changes
            )
        )

    def restore(self, posting: ValuationPosting, **changes: object) -> ValuationPosting:
        """Передаёт полный собственный состав восстановления без внешних оснований."""
        values = {field.name: getattr(posting, field.name) for field in fields(posting)}
        values["identifier"] = values.pop("id")
        return ValuationPosting.restore(**(values | changes))

    def restore_entry(self, entry: ValuationEntry, **changes: object) -> ValuationEntry:
        """Восстанавливает полный состав дочерней записи для проверки локальных инвариантов."""
        values = {field.name: getattr(entry, field.name) for field in fields(entry)}
        values["identifier"] = values.pop("id")
        return ValuationEntry.restore(**(values | changes))

    def multiple_context(self) -> dict[str, object]:
        """Создаёт два реальных прихода в одном проведении и полный ISSUE разных товаров, владельцев, складов и валют."""
        f = self.fx.f
        location = replace(f.second_location, warehouse_id=WarehouseIdVO(uuid4()))
        second = f.position(
            dimensions=replace(
                f.dimensions,
                location_id=location.id,
                inventory_item_id=InventoryItemIdVO(uuid4()),
                owner_id=StockOwnerIdVO(uuid4()),
            ),
            base_uom=UomCodeVO("PCS"),
        )
        positions = (f.first.snapshot(), second.snapshot())
        locations = (f.first_location, location)
        receipt = f.posting(
            entries=(f.entry("5"), f.entry("12", second)), positions=positions
        )
        layers = tuple(
            self.fx.v.create(
                receipt=receipt.receipt_valuation_snapshot(
                    ledger_entry_id=entry.id, position=position, location=loc
                ),
                total_cost=MoneyVO(Decimal(cost), CurrencyVO(currency)),
            )
            for entry, position, loc, cost, currency in zip(
                receipt.entries, positions, locations, ("250", "60"), ("UAH", "USD")
            )
        )
        issue = self.fx.issue_for(
            "2", entries=(f.entry("-2"), f.entry("-3", second)), positions=positions
        )
        results = tuple(
            layer.consume_from_issue(
                issue.issue_valuation_snapshot(
                    ledger_entry_id=entry.id, position=position, location=loc
                ),
                expected_version=0,
                updated_at=self.fx.at,
            )[1]
            for layer, entry, position, loc in zip(
                layers, issue.entries, positions, locations
            )
        )
        return dict(
            posting=issue.snapshot(),
            consumptions=results,
            positions=positions,
            locations=locations,
            entry_bindings=tuple(
                ValuationEntryBindingVO(result.layer.id, ValuationEntryIdVO(uuid4()))
                for result in results
            ),
        )

    def test_single_entry_derives_negative_deltas_and_all_identity_fields(self) -> None:
        """Запись стоимости относится к расходному Ledger, сохраняет измерения и списывает только потреблённую сумму."""
        posting = self.create()
        (entry,) = posting.entries
        self.assertEqual(posting.stock_posting_id, self.fx.posting.id)
        self.assertIs(posting.operation_type, StockOperationType.ISSUE)
        self.assertEqual(posting.stock_posted_at, self.fx.issued_at)
        self.assertEqual(posting.posted_at, self.at)
        self.assertEqual(entry.id, self.binding.entry_id)
        self.assertEqual(entry.ledger_entry_id, self.fx.issue.ledger_entry_id)
        self.assertEqual(entry.layer_id, self.fx.layer.id)
        self.assertEqual(entry.position_id, self.fx.issue.position_id)
        self.assertEqual(entry.inventory_item_id, self.fx.issue.inventory_item_id)
        self.assertEqual(entry.owner_id, self.fx.issue.owner_id)
        self.assertEqual(entry.warehouse_id, self.fx.issue.warehouse_id)
        self.assertEqual(entry.base_uom, self.fx.issue.base_uom)
        self.assertEqual(entry.quantity_delta.value, Decimal("-2"))
        self.assertEqual(entry.cost_delta, MoneyVO(Decimal("-100"), CurrencyVO("UAH")))
        self.assertNotEqual(entry.ledger_entry_id, self.fx.layer.source.ledger_entry_id)

    def test_multiple_entries_preserve_individual_units_currencies_and_costs(
        self,
    ) -> None:
        """Полное проведение сохраняет раздельные стоимости разных единиц и валют без общего некорректного итога."""
        posting = self.create(**self.multiple_context())
        a, b = posting.entries
        self.assertEqual((a.base_uom.value, b.base_uom.value), ("KG", "PCS"))
        self.assertEqual(
            (a.quantity_delta.value, b.quantity_delta.value), (Decimal(-2), Decimal(-3))
        )
        self.assertEqual(
            (a.cost_delta.amount, b.cost_delta.amount), (Decimal(-100), Decimal(-15))
        )
        self.assertEqual(
            (a.cost_delta.currency, b.cost_delta.currency),
            (CurrencyVO("UAH"), CurrencyVO("USD")),
        )
        self.assertNotEqual(a.inventory_item_id, b.inventory_item_id)
        self.assertNotEqual(a.owner_id, b.owner_id)
        self.assertNotEqual(a.warehouse_id, b.warehouse_id)

    def test_result_order_follows_ledger_not_context_order(self) -> None:
        """Перестановка результатов, привязок и контекста не меняет порядок и значения записей стоимости."""
        context = self.multiple_context()
        expected = self.create(**context)
        for name in ("consumptions", "entry_bindings", "positions", "locations"):
            context[name] = tuple(reversed(context[name]))
        self.assertEqual(self.create(**context).entries, expected.entries)

    def test_registration_does_not_consume_layer_again_or_mutate_physical_state(
        self,
    ) -> None:
        """Регистрируется историческая стоимость, а уже изменённый слой и физический остаток сохраняются."""
        before = self.fx.v.restore(self.changed)
        stock = self.fx.posting.snapshot()
        physical = self.fx.f.first.on_hand_qty
        self.create()
        self.assertEqual(self.changed, before)
        self.assertEqual(self.changed.version, 1)
        self.assertEqual(self.changed.remaining_qty.value, Decimal(3))
        self.assertEqual(self.fx.posting.snapshot(), stock)
        self.assertEqual(self.fx.f.first.on_hand_qty, physical)
        self.assertEqual(self.fx.f.first.version, 0)

    def test_historical_consumption_remains_registerable_after_later_layer_update(
        self,
    ) -> None:
        """Свежая версия слоя не подменяет проверенный исторический результат конкретного ISSUE."""
        later_issue = self.fx.produce(self.fx.issue_for("1", posted_at=self.fx.at))
        later, _ = self.fx.consume(self.changed, later_issue)
        self.assertEqual(later.version, 2)
        self.assertEqual(self.create().entries[0].cost_delta.amount, Decimal(-100))
        self.consumption.ensure_valid()

    def test_zero_cost_is_canonical_for_free_issue(self) -> None:
        """Бесплатный расход содержит отрицательное количество и канонический денежный ноль."""
        layer = self.fx.v.create(total_cost=MoneyVO(Decimal(0), CurrencyVO("EUR")))
        _, result = self.fx.consume(layer)
        posting = self.create(
            consumptions=(result,),
            entry_bindings=(ValuationEntryBindingVO(layer.id, self.binding.entry_id),),
        )
        entry = posting.entries[0]
        self.assertEqual(entry.quantity_delta.value, Decimal(-2))
        self.assertEqual(entry.cost_delta, MoneyVO(Decimal(0), CurrencyVO("EUR")))
        self.assertFalse(entry.cost_delta.amount.is_signed())

    def test_three_issue_registrations_preserve_cumulative_rounding(self) -> None:
        """Журнал переносит уже рассчитанные .3333, .3334, .3333 с отрицательным знаком без новой оценки."""
        layer, position = self.fx.case("3", "1", "PCS")
        costs = []
        for offset in range(3):
            stock = self.fx.issue_for(
                "1", position, posted_at=self.fx.issued_at + timedelta(minutes=offset)
            )
            issue = self.fx.produce(stock, position=position.snapshot())
            layer, result = self.fx.consume(layer, issue)
            posting = self.create(
                posting=stock.snapshot(),
                consumptions=(result,),
                positions=(position.snapshot(),),
                entry_bindings=(
                    ValuationEntryBindingVO(layer.id, ValuationEntryIdVO(uuid4())),
                ),
            )
            costs.append(posting.entries[0].cost_delta.amount)
        self.assertEqual(costs, list(map(Decimal, ("-.3333", "-.3334", "-.3333"))))
        self.assertTrue(layer.is_exhausted())

    def test_empty_and_incomplete_consumption_coverage_is_rejected(self) -> None:
        """Нельзя объявить полную оценку при пропуске хотя бы одной записи ISSUE."""
        context = self.multiple_context()
        for results in ((), context["consumptions"][:1]):
            with (
                self.subTest(results=results),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(**(context | dict(consumptions=results)))

    def test_extra_or_foreign_consumption_is_rejected(self) -> None:
        """Самосогласованный результат другого Posting или Ledger не относится к выбранному расходу."""
        for issue in (
            replace(self.fx.issue, posting_id=StockPostingIdVO(uuid4())),
            replace(self.fx.issue, ledger_entry_id=StockLedgerEntryIdVO(uuid4())),
        ):
            result = replace(self.consumption, issue=issue)
            result.ensure_valid()
            with self.assertRaises(ValuationPostingSourceError):
                self.create(consumptions=(result,))
        extra = replace(
            self.consumption,
            layer=replace(self.consumption.layer, id=ValuationLayerIdVO(uuid4())),
            issue=replace(self.fx.issue, ledger_entry_id=StockLedgerEntryIdVO(uuid4())),
        )
        with self.assertRaises(ValuationPostingSourceError):
            self.create(consumptions=(self.consumption, extra))

    def test_missing_ledger_group_or_duplicate_layer_is_rejected(self) -> None:
        """Повтор группы не заменяет пропущенный Ledger; один слой участвует только одним итогом."""
        context = self.multiple_context()
        a, b = context["consumptions"]
        for results, error in (
            (
                (a, replace(a, layer=replace(a.layer, id=b.layer.id))),
                ValuationPostingSourceError,
            ),
            (
                (a, replace(b, layer=replace(b.layer, id=a.layer.id))),
                DuplicateValuationEntryError,
            ),
        ):
            with (
                self.subTest(results=results),
                self.assertRaises(error),
            ):
                self.create(**(context | dict(consumptions=results)))

    def test_bindings_must_cover_all_and_only_used_layers(self) -> None:
        """Пропущенная или лишняя привязка не создаёт запись с автоматически придуманным ID."""
        extra = ValuationEntryBindingVO(
            ValuationLayerIdVO(uuid4()), ValuationEntryIdVO(uuid4())
        )
        for bindings in ((), (extra,), (self.binding, extra)):
            with (
                self.subTest(bindings=bindings),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(entry_bindings=bindings)

    def test_binding_layer_and_entry_ids_cannot_repeat(self) -> None:
        """Разные результаты не могут получить один слой привязки или один ID стоимостной записи."""
        context = self.multiple_context()
        a, b = context["entry_bindings"]
        for bindings in (
            (a, replace(b, entry_id=a.entry_id)),
            (a, replace(b, layer_id=a.layer_id)),
        ):
            with self.assertRaises(DuplicateValuationEntryError):
                self.create(**(context | dict(entry_bindings=bindings)))

    def test_factory_revalidates_consumption_arithmetic_versions_and_cost(self) -> None:
        """Фабрика не доверяет одному наличию типа результата и повторно проверяет весь переход."""
        for changes in (
            dict(quantity=QuantityVO(Decimal(1))),
            dict(cost=MoneyVO(Decimal(99), CurrencyVO("UAH"))),
            dict(version_after=3),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidValuationLayerConsumptionSnapshotError),
            ):
                self.create(consumptions=(replace(self.consumption, **changes),))

    def test_factory_rechecks_item_owner_warehouse_against_physical_context(
        self,
    ) -> None:
        """Самосогласованный результат сравнивается с реальными измерениями ISSUE, а не только с его ID."""
        position = self.fx.f.first.snapshot()
        for dimensions in (
            replace(position.dimensions, inventory_item_id=InventoryItemIdVO(uuid4())),
            replace(position.dimensions, owner_id=StockOwnerIdVO(uuid4())),
        ):
            with self.assertRaises(ValuationPostingSourceError):
                self.create(positions=(replace(position, dimensions=dimensions),))
        with self.assertRaises(ValuationPostingSourceError):
            self.create(
                locations=(
                    replace(
                        self.fx.f.first_location, warehouse_id=WarehouseIdVO(uuid4())
                    ),
                )
            )

    def test_factory_rechecks_position_quantity_unit_and_time_against_ledger(
        self,
    ) -> None:
        """Изменение физического основания при тех же Posting/Entry ID не проходит повторную проверку."""
        stock = self.fx.posting.snapshot()
        entry = stock.entries[0]
        position = self.fx.f.first.snapshot()
        other_id = StockPositionIdVO(uuid4())
        alternatives = (
            dict(
                posting=replace(stock, posted_at=stock.posted_at + timedelta(minutes=1))
            ),
            dict(
                posting=replace(stock, entries=(replace(entry, position_id=other_id),)),
                positions=(replace(position, id=other_id),),
            ),
            dict(
                posting=replace(
                    stock,
                    entries=(
                        replace(
                            entry,
                            quantity_delta=StockDeltaVO(Decimal(-1)),
                            conversion=QuantityConversionSnapshotVO.create(
                                quantity=QuantityVO(Decimal(1)),
                                uom=entry.base_uom,
                                base_uom=entry.base_uom,
                            ),
                        ),
                    ),
                )
            ),
            dict(
                posting=replace(
                    stock,
                    entries=(
                        replace(
                            entry,
                            base_uom=UomCodeVO("PCS"),
                            conversion=QuantityConversionSnapshotVO.create(
                                quantity=QuantityVO(Decimal(2)),
                                uom=UomCodeVO("PCS"),
                                base_uom=UomCodeVO("PCS"),
                            ),
                        ),
                    ),
                ),
                positions=(replace(position, base_uom=UomCodeVO("PCS")),),
            ),
        )
        for changes in alternatives:
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(**changes)

    def test_factory_requires_nominal_snapshot_types_and_tuple_collections(
        self,
    ) -> None:
        """Агрегаты, произвольные элементы и изменяемые коллекции не заменяют входные контракты."""
        for changes in (
            dict(posting=self.fx.posting),
            dict(consumptions=[self.consumption]),
            dict(consumptions=(self.changed,)),
            dict(consumptions=(None,)),
            dict(entry_bindings=[self.binding]),
            dict(entry_bindings=(None,)),
            dict(positions=[]),
            dict(locations=[]),
            dict(locations=(None,)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.create(**changes)

    def test_context_requires_exact_unique_position_and_location_coverage(self) -> None:
        """Проверка всего проведения отклоняет пропуски, повторы и лишние позиции или локации."""
        position = self.fx.f.first.snapshot()
        location = self.fx.f.first_location
        for changes in (
            dict(positions=()),
            dict(positions=(position, position)),
            dict(positions=(position, self.fx.f.second.snapshot())),
            dict(locations=()),
            dict(locations=(location, location)),
            dict(locations=(location, self.fx.f.second_location)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.create(**changes)

    def test_inactive_location_does_not_reprice_historical_issue(self) -> None:
        """Текущее отключение локации не отменяет проверенный исторический расход стоимости."""
        posting = self.create(
            locations=(replace(self.fx.f.first_location, is_active=False),)
        )
        self.assertEqual(posting.entries[0].cost_delta.amount, Decimal(-100))

    def test_receipt_movement_adjustment_and_reversal_are_rejected(self) -> None:
        """Отрицательный знак сам по себе не превращает перемещение или компенсацию в обычный ISSUE."""
        receipt = self.fx.v.posting
        f = self.fx.f
        for stock in (
            receipt.snapshot(),
            f.movement().snapshot(),
            replace(
                self.fx.posting.snapshot(), operation_type=StockOperationType.ADJUSTMENT
            ),
            f.reverse(receipt, posted_at=self.fx.issued_at).snapshot(),
        ):
            with (
                self.subTest(operation=stock.operation_type),
                self.assertRaises(ValuationPostingSourceError),
            ):
                self.create(posting=stock)

    def test_lot_serial_consumption_can_be_registered(self) -> None:
        """Расход одной серии или партии сохраняет связь с исходной позицией и стоимостью слоя."""
        f = self.fx.f
        for serial in (False, True):
            position = f.position(
                dimensions=replace(
                    f.dimensions,
                    lot_id=StockLotIdVO(uuid4()),
                    serial_id=StockSerialIdVO(uuid4()) if serial else None,
                ),
                base_uom=UomCodeVO("PCS") if serial else UomCodeVO("KG"),
            )
            receipt = f.posting(
                entries=(f.entry("1", position),), positions=(position.snapshot(),)
            )
            layer = self.fx.v.create(
                receipt=self.fx.v.produce(receipt, position=position.snapshot())
            )
            stock = self.fx.issue_for("1", position)
            issue = self.fx.produce(stock, position=position.snapshot())
            _, result = self.fx.consume(layer, issue)
            posting = self.create(
                posting=stock.snapshot(),
                consumptions=(result,),
                entry_bindings=(
                    ValuationEntryBindingVO(layer.id, self.binding.entry_id),
                ),
                positions=(position.snapshot(),),
            )
            self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(-1))

    def test_registration_time_must_follow_physical_issue_and_each_consumption(
        self,
    ) -> None:
        """Стоимостной факт не может появиться раньше физического расхода или результата перехода."""
        for at in (
            self.fx.issued_at - timedelta(seconds=1),
            self.consumption.consumed_at - timedelta(microseconds=1),
        ):
            with self.subTest(at=at), self.assertRaises(ValuationPostingTimeError):
                self.create(posted_at=at)
        context = self.multiple_context()
        a, b = context["consumptions"]
        later = replace(b, consumed_at=self.at + timedelta(minutes=1))
        with self.assertRaises(ValuationPostingTimeError):
            self.create(**(context | dict(consumptions=(a, later))))

    def test_registration_normalizes_aware_time_and_allows_consumption_time(
        self,
    ) -> None:
        """Регистрация в тот же момент допустима; смещение нормализуется в UTC."""
        posting = self.create(
            posted_at=self.consumption.consumed_at.astimezone(
                timezone(timedelta(hours=2))
            )
        )
        self.assertEqual(posting.posted_at, self.consumption.consumed_at)
        self.assertEqual(posting.posted_at.utcoffset(), timedelta(0))

    def test_registration_rejects_naive_or_raw_time(self) -> None:
        """Фабрика требует явный aware datetime без чтения часов."""
        for at in (None, "now", self.at.replace(tzinfo=None)):
            with self.subTest(at=at), self.assertRaises(ValuationPostingTimeError):
                self.create(posted_at=at)

    def test_restore_preserves_expense_without_current_context(self) -> None:
        """Историческое проведение восстанавливается из собственных полей без исходных слоёв и их версий."""
        posting = self.create(**self.multiple_context())
        zone = timezone(timedelta(hours=-3))
        restored = self.restore(
            posting,
            stock_posted_at=posting.stock_posted_at.astimezone(zone),
            posted_at=posting.posted_at.astimezone(zone),
        )
        self.assertEqual(restored, posting)
        for entry in posting.entries:
            self.assertEqual(self.restore_entry(entry), entry)

    def test_restore_rejects_raw_operation_or_direction_of_other_operation(
        self,
    ) -> None:
        """Допуск ISSUE не разрешает строку вместо enum или отрицательные записи в приходном корне."""
        posting = self.create()
        for operation in (
            "ISSUE",
            StockOperationType.RECEIPT,
            StockOperationType.ADJUSTMENT,
            StockOperationType.INTERNAL_MOVE,
        ):
            with (
                self.subTest(operation=operation),
                self.assertRaises(InvalidValuationPostingValueError),
            ):
                self.restore(posting, operation_type=operation)

    def test_root_rejects_mixed_directions_even_when_children_are_individually_valid(
        self,
    ) -> None:
        """В одном обычном проведении нельзя смешивать корректные приходные и расходные записи."""
        posting = self.create(**self.multiple_context())
        a, b = posting.entries
        positive = self.restore_entry(
            b,
            quantity_delta=StockDeltaVO(b.quantity_delta.value.copy_abs()),
            cost_delta=MoneyVO(b.cost_delta.amount.copy_abs(), b.cost_delta.currency),
        )
        for operation in (StockOperationType.RECEIPT, StockOperationType.ISSUE):
            with self.assertRaises(InvalidValuationPostingValueError):
                self.restore(posting, operation_type=operation, entries=(a, positive))

    def test_child_rejects_opposite_directions_and_zero_quantity(self) -> None:
        """Локальное правило Entity запрещает противоположные знаки и нулевую количественную дельту."""
        entry = self.create().entries[0]
        for changes in (
            dict(quantity_delta=StockDeltaVO(Decimal(2))),
            dict(cost_delta=MoneyVO(Decimal(100), CurrencyVO("UAH"))),
            dict(quantity_delta=StockDeltaVO(Decimal(0))),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidValuationEntryError),
            ):
                self.restore_entry(entry, **changes)

    def test_zero_cost_is_valid_in_both_directions(self) -> None:
        """Денежный ноль не требует отрицательного знака и допустим для прихода и расхода."""
        entry = self.create().entries[0]
        for quantity in ("2", "-2"):
            valid = self.restore_entry(
                entry,
                quantity_delta=StockDeltaVO(Decimal(quantity)),
                cost_delta=MoneyVO(Decimal(0), CurrencyVO("UAH")),
            )
            valid.ensure_valid()

    def test_negative_noncanonical_money_is_rejected_on_restore(self) -> None:
        """Расширение знаков не разрешает повторно округлить повреждённую сохранённую сумму расхода."""
        entry = self.create().entries[0]
        with self.assertRaises(InvalidValuationEntryError):
            self.restore_entry(
                entry, cost_delta=self.fx.malformed_money(Decimal("-100.00001"))
            )

    def test_facts_and_entries_remain_immutable(self) -> None:
        """Стоимостное проведение и его дочерние записи не предоставляют прямого изменения."""
        posting = self.create()
        for obj, name, value in (
            (posting, "operation_type", StockOperationType.RECEIPT),
            (posting.entries[0], "quantity_delta", StockDeltaVO(Decimal(1))),
        ):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, name, value)

    def test_hostile_decimal_context_does_not_round_signed_values(self) -> None:
        """Смена знака количества и денег не теряет разряды во внешнем Decimal context."""
        layer, position = self.fx.case("123.456789", "9876.5432")
        stock = self.fx.issue_for("12.3456789", position)
        issue = self.fx.produce(stock, position=position.snapshot())
        _, result = self.fx.consume(layer, issue)
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            posting = self.create(
                posting=stock.snapshot(),
                consumptions=(result,),
                positions=(position.snapshot(),),
                entry_bindings=(
                    ValuationEntryBindingVO(layer.id, self.binding.entry_id),
                ),
            )
            restored = self.restore(posting)
        self.assertEqual(
            restored.entries[0].quantity_delta.value, Decimal("-12.3456789")
        )
        self.assertEqual(restored.entries[0].cost_delta.amount, Decimal("-987.6543"))


if __name__ == "__main__":
    unittest.main()
