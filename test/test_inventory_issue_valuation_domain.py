"""Потребление стоимости одного слоя по полной записи фактического ISSUE."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_valuation_layer_domain as valuation_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_issue_valuation import (
    StockIssueValuationPolicy,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.error import (
    StockIssueValuationSourceError,
)
from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.valuation_layer.aggregate import ValuationLayer
from src.modules.inventory.domain.valuation_layer.consumption_snapshot import (
    ValuationLayerConsumptionSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerConsumptionSnapshotError,
    InvalidValuationLayerValueError,
    ValuationLayerConsumptionError,
    ValuationLayerIssueMismatchError,
    ValuationLayerTimeError,
    ValuationLayerVersionConflictError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class IssueValuationDomainTests(unittest.TestCase):
    """Проверяет основания физического расхода, переход слоя и проверяемый результат стоимости."""

    def setUp(self) -> None:
        """Готовит слой пяти KG за 250 UAH и обычный ISSUE двух KG исходной позиции."""
        self.v = valuation_fixture.ValuationLayerDomainTests()
        self.v.setUp()
        self.f = self.v.f
        self.layer = self.v.create()
        self.issued_at = self.layer.created_at + timedelta(hours=1)
        self.at = self.issued_at + timedelta(hours=1)
        self.posting = self.issue_for("2")
        self.issue = self.produce()

    def issue_for(
        self, quantity: str, position: StockPosition | None = None, **changes: object
    ) -> StockPosting:
        """Создаёт реальную отрицательную запись обычного ISSUE без применения к физическому остатку."""
        target = self.f.first if position is None else position
        return self.f.posting(
            **(
                dict(
                    operation_type=StockOperationType.ISSUE,
                    posted_at=self.issued_at,
                    entries=(self.f.entry("-" + quantity, target),),
                    positions=(target.snapshot(),),
                )
                | changes
            )
        )

    def produce(
        self, posting: StockPosting | None = None, **changes: object
    ) -> StockIssueValuationSnapshot:
        """Получает специализированное основание через публичный метод физического проведения."""
        target = self.posting if posting is None else posting
        return target.issue_valuation_snapshot(
            **(
                dict(
                    ledger_entry_id=target.entries[0].id,
                    position=self.f.first.snapshot(),
                    location=self.f.first_location,
                )
                | changes
            )
        )

    def consume(
        self,
        layer: ValuationLayer | None = None,
        issue: StockIssueValuationSnapshot | None = None,
        **changes: object,
    ) -> tuple[ValuationLayer, ValuationLayerConsumptionSnapshot]:
        """Потребляет проверенное основание с актуальной версией и явным моментом регистрации."""
        target = self.layer if layer is None else layer
        return target.consume_from_issue(
            self.issue if issue is None else issue,
            **(
                dict(
                    expected_version=target.version,
                    updated_at=self.at,
                )
                | changes
            ),
        )

    def case(
        self, quantity: str, cost: str, unit: str = "KG"
    ) -> tuple[ValuationLayer, StockPosition]:
        """Создаёт самостоятельное исходное поступление и слой для дробных или штучных сценариев."""
        position = self.f.position(base_uom=UomCodeVO(unit))
        receipt = self.f.posting(
            entries=(self.f.entry(quantity, position),),
            positions=(position.snapshot(),),
        )
        layer = self.v.create(
            receipt=self.v.produce(receipt, position=position.snapshot()),
            total_cost=MoneyVO(Decimal(cost), CurrencyVO("UAH")),
        )
        return layer, position

    def malformed_quantity(self, value: object) -> QuantityVO:
        """Обходит конструктор для проверки защиты от повреждённого сохранённого количества."""
        quantity = object.__new__(QuantityVO)
        object.__setattr__(quantity, "value", value)
        return quantity

    def malformed_money(self, value: object) -> MoneyVO:
        """Обходит конструктор для проверки конечности и сохранённой точности денег в результате."""
        money = object.__new__(MoneyVO)
        object.__setattr__(money, "amount", value)
        object.__setattr__(money, "currency", CurrencyVO("UAH"))
        return money

    def test_producer_derives_full_identity_positive_magnitude_and_historical_time(
        self,
    ) -> None:
        """Снимок расхода выводит все значения из выбранной отрицательной записи и её контекста."""
        self.assertEqual(self.issue.posting_id, self.posting.id)
        self.assertEqual(self.issue.ledger_entry_id, self.posting.entries[0].id)
        self.assertEqual(self.issue.position_id, self.f.first.id)
        self.assertEqual(self.issue.inventory_item_id, self.layer.inventory_item_id)
        self.assertEqual(self.issue.owner_id, self.layer.owner_id)
        self.assertEqual(self.issue.warehouse_id, self.layer.warehouse_id)
        self.assertEqual(self.issue.base_uom, UomCodeVO("KG"))
        self.assertEqual(self.issue.quantity, QuantityVO(Decimal(2)))
        self.assertEqual(self.issue.issued_at, self.posting.posted_at)

    def test_producer_selects_one_entry_without_summing_whole_posting(self) -> None:
        """Оценка выбранной записи не присваивает ей количество остальных строк ISSUE."""
        posting = self.issue_for(
            "2",
            entries=(self.f.entry("-2"), self.f.entry("-3", self.f.second)),
            positions=(self.f.first.snapshot(), self.f.second.snapshot()),
        )
        issue = self.produce(
            posting,
            ledger_entry_id=posting.entries[1].id,
            position=self.f.second.snapshot(),
            location=self.f.second_location,
        )
        self.assertEqual(issue.quantity.value, Decimal(3))
        self.assertEqual(issue.position_id, self.f.second.id)

    def test_producer_rejects_unknown_or_raw_ledger_identifier(self) -> None:
        """Без существующей номинальной ссылки запись физического расхода не выбирается."""
        for identifier in (StockLedgerEntryIdVO(uuid4()), uuid4(), None):
            with (
                self.subTest(identifier=identifier),
                self.assertRaises(StockIssueValuationSourceError),
            ):
                self.produce(ledger_entry_id=identifier)

    def test_producer_rejects_wrong_operation_and_all_reversals(self) -> None:
        """Даже отрицательная компенсация прихода или сторона перемещения не являются обычным ISSUE."""
        receipt = self.v.posting
        adjustment = replace(
            self.posting.snapshot(), operation_type=StockOperationType.ADJUSTMENT
        )
        for source in (
            receipt.snapshot(),
            self.f.movement().snapshot(),
            adjustment,
            self.f.reverse(receipt).snapshot(),
            self.f.reverse(self.posting, posted_at=self.at).snapshot(),
        ):
            with (
                self.subTest(operation=source.operation_type),
                self.assertRaises(StockIssueValuationSourceError),
            ):
                StockIssueValuationPolicy.build_snapshot(
                    posting=source,
                    ledger_entry_id=source.entries[0].id,
                    position=self.f.first.snapshot(),
                    location=self.f.first_location,
                )

    def test_producer_rejects_wrong_position_unit_or_location(self) -> None:
        """Позиция записи, её базовая единица и принадлежность локации проверяются до экспорта."""
        for changes in (
            dict(position=self.f.second.snapshot()),
            dict(position=replace(self.f.first.snapshot(), base_uom=UomCodeVO("G"))),
            dict(location=self.f.second_location),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.produce(**changes)

    def test_producer_requires_snapshots_instead_of_aggregate_or_raw_values(
        self,
    ) -> None:
        """Контракт межагрегатного взаимодействия не принимает произвольные объекты."""
        for posting, position, location in (
            (self.posting, self.f.first.snapshot(), self.f.first_location),
            (self.posting.snapshot(), self.f.first, self.f.first_location),
            (self.posting.snapshot(), self.f.first.snapshot(), None),
        ):
            with self.assertRaises(StockIssueValuationSourceError):
                StockIssueValuationPolicy.build_snapshot(
                    posting=posting,
                    ledger_entry_id=self.posting.entries[0].id,
                    position=position,
                    location=location,
                )

    def test_producer_preserves_historical_conversion_and_ignores_inactive_location(
        self,
    ) -> None:
        """Современный коэффициент и отключение локации не переписывают проведённый расход."""
        entry = self.f.entry("-2")
        historical = replace(
            entry,
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal(1000)), UomCodeVO("G"), Decimal(".002")
            ),
        )
        posting = self.v.historical_posting(
            historical,
            operation_type=StockOperationType.ISSUE,
            posted_at=self.issued_at,
        )
        issue = self.produce(
            posting, location=replace(self.f.first_location, is_active=False)
        )
        layer, result = self.consume(issue=issue)
        self.assertEqual(layer.remaining_qty.value, Decimal(3))
        self.assertEqual(result.cost.amount, Decimal(100))

    def test_partial_consumption_returns_new_layer_and_complete_transition(
        self,
    ) -> None:
        """Расход двух KG оставляет три KG за 150 UAH и результат потребления 100 UAH."""
        layer, result = self.consume()
        self.assertEqual(layer.remaining_qty.value, Decimal(3))
        self.assertEqual(layer.remaining_cost.amount, Decimal(150))
        self.assertEqual(layer.version, 1)
        self.assertEqual(layer.updated_at, self.at)
        self.assertEqual(result.layer, self.layer.receipt_valuation_snapshot())
        self.assertIs(result.issue, self.issue)
        self.assertEqual(result.quantity, self.issue.quantity)
        self.assertEqual(result.cost, MoneyVO(Decimal(100), CurrencyVO("UAH")))
        self.assertEqual(
            (result.remaining_qty_before.value, result.remaining_qty_after.value),
            (Decimal(5), Decimal(3)),
        )
        self.assertEqual(
            (result.remaining_cost_before.amount, result.remaining_cost_after.amount),
            (Decimal(250), Decimal(150)),
        )
        self.assertEqual((result.version_before, result.version_after), (0, 1))
        self.assertEqual(result.updated_at_before, self.layer.updated_at)
        self.assertEqual(result.consumed_at, layer.updated_at)
        result.ensure_valid()

    def test_full_consumption_zeroes_both_balances(self) -> None:
        """Полный расход оставляет точный ноль количества и стоимости без корректировочной записи."""
        issue = self.produce(self.issue_for("5"))
        layer, result = self.consume(issue=issue)
        self.assertTrue(layer.is_exhausted())
        self.assertEqual(layer.remaining_cost.amount, Decimal(0))
        self.assertEqual(result.cost.amount, Decimal(250))

    def test_cumulative_rounding_over_three_actual_issue_postings(self) -> None:
        """Три отдельных фактических ISSUE одной PCS распределяют стоимость как .3333, .3334, .3333."""
        layer, position = self.case("3", "1", "PCS")
        costs = []
        for offset in range(3):
            posting = self.issue_for(
                "1", position, posted_at=self.issued_at + timedelta(minutes=offset)
            )
            issue = self.produce(posting, position=position.snapshot())
            layer, result = self.consume(layer, issue)
            costs.append(result.cost.amount)
        self.assertEqual(costs, list(map(Decimal, (".3333", ".3334", ".3333"))))
        self.assertTrue(layer.is_exhausted())
        self.assertEqual(layer.version, 3)

    def test_free_and_rounded_zero_cost_remain_valid_consumptions(self) -> None:
        """Нулевая стоимость допустима и для бесплатного слоя, и после накопленного округления."""
        for original_cost in ("0", ".0001"):
            layer, position = self.case("3", original_cost, "PCS")
            issue = self.produce(
                self.issue_for("1", position), position=position.snapshot()
            )
            costs = []
            for _ in range(3):
                layer, result = self.consume(layer, issue)
                costs.append(result.cost.amount)
            self.assertTrue(layer.is_exhausted())
            self.assertEqual(sum(costs), Decimal(original_cost))
            self.assertEqual(costs[-1], Decimal(0))

    def test_fractional_weight_and_liquid_use_full_base_quantity(self) -> None:
        """Дробное количество расхода в KG или L не округляется до единицы или современного шага товара."""
        for unit in ("KG", "L"):
            layer, position = self.case(".125", "6.25", unit)
            issue = self.produce(
                self.issue_for(".03125", position), position=position.snapshot()
            )
            changed, result = self.consume(layer, issue)
            self.assertEqual(changed.remaining_qty.value, Decimal(".09375"))
            self.assertEqual(result.cost.amount, Decimal("1.5625"))

    def test_source_root_and_physical_stock_remain_unchanged(self) -> None:
        """Стоимость возвращает новый слой, не изменяя старый, физический журнал, позицию и её версию."""
        before = self.v.restore(self.layer)
        stock = self.posting.snapshot()
        balance = self.f.first.on_hand_qty
        layer, result = self.consume()
        self.assertIsNot(layer, self.layer)
        self.assertEqual(self.layer, before)
        self.assertIs(layer.cost_basis, self.layer.cost_basis)
        self.assertIs(layer.source, self.layer.source)
        self.assertEqual(self.posting.snapshot(), stock)
        self.assertEqual(self.f.first.on_hand_qty, balance)
        self.assertEqual(self.f.first.version, 0)
        for target, name, value in (
            (result, "cost", self.v.cost),
            (self.issue, "quantity", QuantityVO(Decimal(1))),
        ):
            with self.assertRaises(FrozenInstanceError):
                setattr(target, name, value)

    def test_consume_requires_specialized_issue_snapshot(self) -> None:
        """Приход, физическое проведение или отсутствие основания не заменяют снимок ISSUE."""
        for issue in (None, self.posting, self.v.receipt):
            with (
                self.subTest(issue=issue),
                self.assertRaises(ValuationLayerIssueMismatchError),
            ):
                self.layer.consume_from_issue(
                    issue, expected_version=0, updated_at=self.at
                )

    def test_consume_rejects_other_item_owner_warehouse_uom_and_position(self) -> None:
        """Совпадения части измерений недостаточно для использования чужого стоимостного слоя."""
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
            dict(position_id=StockPositionIdVO(uuid4())),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(ValuationLayerIssueMismatchError),
            ):
                self.consume(issue=replace(self.issue, **changes))

    def test_actual_issue_from_another_location_cannot_consume_original_layer(
        self,
    ) -> None:
        """Даже тот же товар, владелец и склад не разрешают списать стоимость из другой исходной позиции."""
        posting = self.issue_for("2", self.f.second)
        issue = self.produce(
            posting, position=self.f.second.snapshot(), location=self.f.second_location
        )
        with self.assertRaises(ValuationLayerIssueMismatchError):
            self.consume(issue=issue)

    def test_overconsumption_and_exhausted_layer_are_rejected_atomically(self) -> None:
        """Запись ISSUE погашается целиком одним слоем или отклоняется без частичного результата."""
        before = self.v.restore(self.layer)
        with self.assertRaises(ValuationLayerConsumptionError):
            self.consume(issue=self.produce(self.issue_for("6")))
        self.assertEqual(self.layer, before)
        exhausted, _ = self.consume(issue=self.produce(self.issue_for("5")))
        with self.assertRaises(ValuationLayerConsumptionError):
            self.consume(exhausted)

    def test_stale_version_rejects_retry_but_new_version_is_not_global_deduplication(
        self,
    ) -> None:
        """Старая версия отклоняется; предотвращение повтора того же ISSUE с новой версией остаётся хранению."""
        layer, _ = self.consume()
        with self.assertRaises(ValuationLayerVersionConflictError):
            self.consume(layer, expected_version=0)
        another, _ = self.consume(layer)
        self.assertEqual(another.remaining_qty.value, Decimal(1))
        self.assertEqual(another.version, 2)

    def test_expected_version_requires_strict_nonnegative_integer(self) -> None:
        """Булевы значения, дроби, строки и отрицательные числа не являются версиями команды."""
        for version in (False, True, -1, 0.0, "0", None):
            with (
                self.subTest(version=version),
                self.assertRaises(InvalidValuationLayerValueError),
            ):
                self.consume(expected_version=version)

    def test_physical_issue_cannot_precede_receipt(self) -> None:
        """Даже достаточный текущий остаток не позволяет использовать слой из будущего относительно ISSUE."""
        issue = self.produce(
            self.issue_for("2", posted_at=self.layer.received_at - timedelta(seconds=1))
        )
        with self.assertRaises(ValuationLayerTimeError):
            self.consume(issue=issue)

    def test_registration_cannot_precede_issue_or_previous_update(self) -> None:
        """Момент перехода должен учитывать и физический расход, и предыдущую историю слоя."""
        with self.assertRaises(ValuationLayerTimeError):
            self.consume(updated_at=self.issue.issued_at - timedelta(seconds=1))
        layer, _ = self.consume(updated_at=self.at + timedelta(hours=1))
        with self.assertRaises(ValuationLayerTimeError):
            self.consume(layer, updated_at=self.at)

    def test_registration_normalizes_aware_time_and_allows_equality(self) -> None:
        """Явное смещение превращается в UTC; регистрация в момент ISSUE допустима."""
        layer, result = self.consume(
            updated_at=self.issue.issued_at.astimezone(timezone(timedelta(hours=2)))
        )
        self.assertEqual(layer.updated_at, self.issue.issued_at)
        self.assertEqual(result.consumed_at.utcoffset(), timedelta(0))

    def test_registration_rejects_naive_or_raw_time(self) -> None:
        """Переход не читает часы и требует явный aware datetime."""
        for at in (self.at.replace(tzinfo=None), "now", None):
            with self.subTest(at=at), self.assertRaises(ValuationLayerTimeError):
                self.consume(updated_at=at)

    def test_cost_registration_may_happen_after_physical_issue(self) -> None:
        """Позднее заполнение стоимости не меняет порядок физических поступления и расхода."""
        layer = self.v.create(created_at=self.at)
        changed, result = self.consume(layer, updated_at=self.at)
        self.assertEqual(result.quantity.value, Decimal(2))
        self.assertEqual(changed.remaining_cost.amount, Decimal(150))

    def test_lot_and_serial_issue_preserve_exact_source_position(self) -> None:
        """Режимы прослеживаемости используют исходную позицию; свежие сроки партии не запрашиваются."""
        for serial in (False, True):
            position = self.f.position(
                dimensions=replace(
                    self.f.dimensions,
                    lot_id=StockLotIdVO(uuid4()),
                    serial_id=StockSerialIdVO(uuid4()) if serial else None,
                ),
                base_uom=UomCodeVO("PCS") if serial else UomCodeVO("KG"),
            )
            receipt = self.f.posting(
                entries=(self.f.entry("1", position),), positions=(position.snapshot(),)
            )
            layer = self.v.create(
                receipt=self.v.produce(receipt, position=position.snapshot())
            )
            issue = self.produce(
                self.issue_for("1", position), position=position.snapshot()
            )
            changed, result = self.consume(layer, issue)
            self.assertTrue(changed.is_exhausted())
            self.assertEqual(result.layer.source.position_id, position.id)

    def test_serial_issue_requires_one_pcs_even_in_restored_history(self) -> None:
        """Повторная проверка физического основания отклоняет несколько штук одной серии."""
        position = self.f.position(
            dimensions=replace(self.f.dimensions, serial_id=StockSerialIdVO(uuid4())),
            base_uom=UomCodeVO("PCS"),
        )
        posting = self.v.historical_posting(
            self.f.entry("-2", position),
            operation_type=StockOperationType.ISSUE,
            posted_at=self.issued_at,
        )
        with self.assertRaises(InventoryError):
            self.produce(posting, position=position.snapshot())

    def test_issue_snapshot_validates_all_nominal_fields(self) -> None:
        """Аннотации не заменяют проверки номинальных ссылок и единицы готового снимка."""
        for name in (
            "posting_id",
            "ledger_entry_id",
            "position_id",
            "inventory_item_id",
            "owner_id",
            "warehouse_id",
            "base_uom",
            "quantity",
        ):
            with self.subTest(name=name), self.assertRaises(InventoryError):
                replace(self.issue, **{name: None}).ensure_valid()

    def test_issue_snapshot_rejects_nonpositive_nonfinite_or_raw_quantity(self) -> None:
        """Положительный модуль расхода проверяется и после обхода конструктора QuantityVO."""
        for value in (
            Decimal(0),
            Decimal(-1),
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            "1",
        ):
            with self.subTest(value=value), self.assertRaises(InventoryError):
                replace(
                    self.issue, quantity=self.malformed_quantity(value)
                ).ensure_valid()

    def test_issue_snapshot_requires_saved_utc_time(self) -> None:
        """Готовый контракт расхода хранит UTC, а не произвольное aware-смещение."""
        for at in (
            None,
            self.issued_at.replace(tzinfo=None),
            self.issued_at.astimezone(timezone(timedelta(hours=2))),
        ):
            with self.subTest(at=at), self.assertRaises(InventoryError):
                replace(self.issue, issued_at=at).ensure_valid()

    def test_result_rejects_wrong_basis_or_issue_dimensions(self) -> None:
        """Результат нельзя перепривязать к несовместимому слою или расходу другого владельца."""
        _, result = self.consume()
        for changes in (
            dict(layer=None),
            dict(issue=None),
            dict(issue=replace(self.issue, owner_id=StockOwnerIdVO(uuid4()))),
            dict(
                layer=replace(
                    result.layer, inventory_item_id=InventoryItemIdVO(uuid4())
                )
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(result, **changes).ensure_valid()

    def test_result_requires_valid_issue_part_and_exact_difference(self) -> None:
        """Количество части должно точно соответствовать сохранённой разнице остатков."""
        _, result = self.consume()
        for changes in (
            dict(quantity=QuantityVO(Decimal(1))),
            dict(remaining_qty_after=QuantityVO(Decimal(2))),
            dict(remaining_qty_before=QuantityVO(Decimal(1))),
            dict(quantity=self.malformed_quantity(Decimal("NaN"))),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidValuationLayerConsumptionSnapshotError),
            ):
                replace(result, **changes).ensure_valid()

    def test_result_rejects_quantities_outside_original_basis(self) -> None:
        """Оба остатка проверяются по диапазону первоначального количества и конечности."""
        _, result = self.consume()
        for name in ("remaining_qty_before", "remaining_qty_after"):
            for quantity in (
                QuantityVO(Decimal(6)),
                None,
                self.malformed_quantity(Decimal("Infinity")),
            ):
                with (
                    self.subTest(name=name, quantity=quantity),
                    self.assertRaises(InventoryError),
                ):
                    replace(result, **{name: quantity}).ensure_valid()

    def test_result_requires_cumulative_costs_on_both_sides_and_exact_consumed_cost(
        self,
    ) -> None:
        """Произвольная промежуточная стоимость и несогласованная разница денег отклоняются."""
        _, result = self.consume()
        for changes in (
            dict(remaining_cost_before=MoneyVO(Decimal("249.9999"), CurrencyVO("UAH"))),
            dict(remaining_cost_after=MoneyVO(Decimal("149.9999"), CurrencyVO("UAH"))),
            dict(cost=MoneyVO(Decimal("99.9999"), CurrencyVO("UAH"))),
            dict(cost=MoneyVO(Decimal(-100), CurrencyVO("UAH"))),
            dict(cost=MoneyVO(Decimal(100), CurrencyVO("EUR"))),
            dict(remaining_cost_after=MoneyVO(Decimal(150), CurrencyVO("EUR"))),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidValuationLayerConsumptionSnapshotError),
            ):
                replace(result, **changes).ensure_valid()

    def test_result_rejects_nonfinite_and_noncanonical_money(self) -> None:
        """Готовые суммы не округляются повторно и не могут скрывать неконечное сохранённое значение."""
        _, result = self.consume()
        for name in ("cost", "remaining_cost_before", "remaining_cost_after"):
            for value in (
                Decimal("NaN"),
                Decimal("sNaN"),
                Decimal("Infinity"),
                Decimal("100.00001"),
                "100",
            ):
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(InvalidValuationLayerConsumptionSnapshotError),
                ):
                    replace(
                        result, **{name: self.malformed_money(value)}
                    ).ensure_valid()

    def test_result_requires_strict_consecutive_versions(self) -> None:
        """Версии результата строго целые, неотрицательные и отличаются ровно на один."""
        _, result = self.consume()
        for before, after in (
            (False, 1),
            (0, True),
            (-1, 0),
            (0, 0),
            (0, 2),
            ("0", 1),
            (0, 1.0),
        ):
            with (
                self.subTest(before=before, after=after),
                self.assertRaises(InvalidValuationLayerConsumptionSnapshotError),
            ):
                replace(
                    result, version_before=before, version_after=after
                ).ensure_valid()

    def test_result_checks_entire_saved_utc_chronology(self) -> None:
        """Время результата учитывает регистрацию слоя, предыдущее изменение и физический расход."""
        _, result = self.consume()
        for changes in (
            dict(updated_at_before=self.layer.created_at - timedelta(seconds=1)),
            dict(consumed_at=self.issue.issued_at - timedelta(seconds=1)),
            dict(updated_at_before=self.at + timedelta(seconds=1)),
            dict(consumed_at=self.at.replace(tzinfo=None)),
            dict(consumed_at=self.at.astimezone(timezone(timedelta(hours=2)))),
            dict(updated_at_before=None),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(result, **changes).ensure_valid()

    def test_corrupted_root_is_revalidated_before_issue_consumption(self) -> None:
        """Прямое создание несогласованного остатка корня не обходит проверки нового метода."""
        broken = replace(
            self.layer, remaining_cost=MoneyVO(Decimal(0), CurrencyVO("UAH"))
        )
        with self.assertRaises(InvalidValuationLayerValueError):
            self.consume(broken)

    def test_result_revalidation_does_not_require_current_layer_or_foreign_aggregate(
        self,
    ) -> None:
        """Все данные для проверки результата хранятся в нём без чтения текущего остатка и журналов."""
        changed, result = self.consume()
        self.consume(changed)
        result.ensure_valid()
        restored = self.v.restore(changed)
        self.assertEqual(restored, changed)
        self.assertEqual(result.version_after, 1)

    def test_hostile_decimal_context_preserves_magnitude_cost_and_result(self) -> None:
        """Малая точность и traps не влияют на положительный модуль дельты и накопленную стоимость."""
        layer, position = self.case("123.456789", "9876.5432")
        posting = self.issue_for("12.3456789", position)
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            issue = self.produce(posting, position=position.snapshot())
            changed, result = self.consume(layer, issue)
            result.ensure_valid()
        self.assertEqual(issue.quantity.value, Decimal("12.3456789"))
        self.assertEqual(changed.remaining_qty.value, Decimal("111.1111101"))
        self.assertEqual(result.cost.amount, Decimal("987.6543"))


if __name__ == "__main__":
    unittest.main()
