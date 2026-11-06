"""Первоначальная стоимость слоя по конкретной положительной записи проведённого прихода."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_stock_posting_domain as posting_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.receipt_valuation_snapshot import (
    StockReceiptValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
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
from src.modules.inventory.domain.stock_posting.value_object.posting_source import (
    PostingSourceVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.valuation_layer.aggregate import ValuationLayer
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.source import (
    ValuationLayerSourceVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.cost_basis import (
    CostBasisVO,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidCostBasisError,
    ValuationLayerTimeError,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO


class ValuationLayerDomainTests(unittest.TestCase):
    """Проверяет происхождение, типы, историческую точность и неизменность стоимостной фиксации."""

    def setUp(self) -> None:
        """Готовит реальный StockPosting прихода пяти KG и стоимость 250 UAH."""
        self.f = posting_fixture.StockPostingDomainTests()
        self.f.setUp()
        self.posting = self.f.posting()
        self.receipt = self.produce()
        self.at = self.f.time + timedelta(days=1)
        self.cost = MoneyVO(Decimal("250"), CurrencyVO("UAH"))

    def produce(
        self, posting: StockPosting | None = None, **changes: object
    ) -> StockReceiptValuationSnapshot:
        """Выделяет одну запись фактического проведения через публичный метод корня."""
        target = self.posting if posting is None else posting
        return target.receipt_valuation_snapshot(
            **(
                dict(
                    ledger_entry_id=target.entries[0].id,
                    position=self.f.first.snapshot(),
                    location=self.f.first_location,
                )
                | changes
            )
        )

    def create(self, **changes: object) -> ValuationLayer:
        """Создаёт слой по готовому основанию и явно выбранной полной стоимости."""
        return ValuationLayer.create_from_receipt(
            **(
                dict(
                    identifier=ValuationLayerIdVO(uuid4()),
                    receipt=self.receipt,
                    total_cost=self.cost,
                    created_at=self.at,
                )
                | changes
            )
        )

    def restore(self, layer: ValuationLayer, **changes: object) -> ValuationLayer:
        """Восстанавливает полный собственный состав без StockPosting и текущих справочников."""
        values = {field.name: getattr(layer, field.name) for field in fields(layer)}
        values["identifier"] = values.pop("id")
        return ValuationLayer.restore(**(values | changes))

    def historical_posting(
        self, entry: StockLedgerEntry, **changes: object
    ) -> StockPosting:
        """Восстанавливает проведённую историю без перепроверки её коэффициента текущим каталогом."""
        return StockPosting.restore(
            **(
                dict(
                    identifier=StockPostingIdVO(uuid4()),
                    source=self.f.source,
                    operation_type=StockOperationType.RECEIPT,
                    posted_at=self.f.time,
                    entries=(entry,),
                    reversal_of_id=None,
                )
                | changes
            )
        )

    def test_create_derives_all_receipt_fields_and_preserves_full_money(self) -> None:
        """Слой получает идентичность/количество из источника, а полную стоимость сохраняет отдельно."""
        layer = self.create()
        self.assertEqual(
            layer.source,
            ValuationLayerSourceVO(
                self.posting.id, self.posting.entries[0].id, self.f.first.id
            ),
        )
        self.assertEqual(layer.inventory_item_id, self.f.dimensions.inventory_item_id)
        self.assertEqual(layer.owner_id, self.f.dimensions.owner_id)
        self.assertEqual(layer.warehouse_id, self.f.warehouse.id)
        self.assertEqual(layer.base_uom, UomCodeVO("KG"))
        self.assertEqual(layer.cost_basis.quantity, QuantityVO(Decimal(5)))
        self.assertIs(layer.cost_basis.total_cost, self.cost)
        self.assertEqual(layer.received_at, self.posting.posted_at)
        self.assertEqual(layer.created_at, self.at)

    def test_source_snapshot_is_positive_canonical_and_immutable(self) -> None:
        """Основание не хранит цену и не меняет время фактического прихода."""
        self.receipt.ensure_valid()
        self.assertEqual(self.receipt.quantity, QuantityVO(Decimal(5)))
        self.assertEqual(self.receipt.received_at, self.f.time)
        with self.assertRaises(FrozenInstanceError):
            self.receipt.quantity = QuantityVO(Decimal(10))

    def test_producer_and_layer_do_not_change_position_or_posting(self) -> None:
        """Стоимость не применяется к физическому остатку и не создаёт второе движение."""
        before = self.posting.snapshot()
        balance = self.f.first.on_hand_qty
        self.create()
        self.assertEqual(self.posting.snapshot(), before)
        self.assertEqual(self.f.first.on_hand_qty, balance)
        self.assertEqual(self.f.first.version, 0)

    def test_multiple_receipt_entries_produce_individual_layers(self) -> None:
        """Количество и стоимость выбираются по записи, а не по сумме всего прихода."""
        first = self.f.entry("5")
        second = self.f.entry("7", self.f.second)
        posting = self.f.posting(
            entries=(first, second),
            positions=(self.f.first.snapshot(), self.f.second.snapshot()),
        )
        a = self.produce(posting, ledger_entry_id=first.id)
        b = self.produce(
            posting,
            ledger_entry_id=second.id,
            position=self.f.second.snapshot(),
            location=self.f.second_location,
        )
        layer_a = self.create(
            receipt=a, total_cost=MoneyVO(Decimal(250), CurrencyVO("UAH"))
        )
        layer_b = self.create(
            receipt=b, total_cost=MoneyVO(Decimal(420), CurrencyVO("UAH"))
        )
        self.assertEqual(
            (layer_a.cost_basis.quantity.value, layer_b.cost_basis.quantity.value),
            (Decimal(5), Decimal(7)),
        )
        self.assertNotEqual(
            layer_a.source.ledger_entry_id, layer_b.source.ledger_entry_id
        )
        self.assertEqual(layer_b.source.position_id, self.f.second.id)

    def test_pcs_kg_and_litre_receipts_use_their_base_quantities(self) -> None:
        """Количество и единица сохраняются для штук, дробного веса и жидкости."""
        for unit, quantity in (("PCS", "12"), ("KG", "0.125"), ("L", "2.375")):
            with self.subTest(unit=unit):
                item = replace(
                    self.f.item.stock_snapshot(),
                    inventory_item_id=InventoryItemIdVO(uuid4()),
                    base_uom=UomCodeVO(unit),
                    quantity_rules=QuantityRulesVO(
                        Decimal(1) if unit == "PCS" else Decimal(".001")
                    ),
                )
                dimensions = replace(
                    self.f.dimensions, inventory_item_id=item.inventory_item_id
                )
                position = StockPosition.create(
                    identifier=StockPositionIdVO(uuid4()),
                    dimensions=dimensions,
                    inventory_item=item,
                    location=self.f.first_location,
                    warehouse=self.f.warehouse,
                )
                entry = self.f.entry(quantity, position)
                posting = self.f.posting(
                    entries=(entry,), positions=(position.snapshot(),)
                )
                receipt = self.produce(posting, position=position.snapshot())
                layer = self.create(receipt=receipt)
                self.assertEqual(layer.base_uom, item.base_uom)
                self.assertEqual(
                    layer.cost_basis.quantity, QuantityVO(Decimal(quantity))
                )

    def test_cost_basis_accepts_free_receipt_and_rejects_negative_cost(self) -> None:
        """Нулевая закупочная стоимость допустима, отрицательная не является стоимостью поступления."""
        free = self.create(total_cost=MoneyVO(Decimal(0), CurrencyVO("USD")))
        self.assertEqual(free.cost_basis.total_cost.amount, Decimal(0))
        with self.assertRaises(InvalidCostBasisError):
            self.create(total_cost=MoneyVO(Decimal("-1"), CurrencyVO("UAH")))

    def test_money_rounding_and_currency_contract_are_reused(self) -> None:
        """Сохраняется готовый MoneyVO с его четырьмя знаками и нормализованной валютой."""
        cost = MoneyVO(Decimal("10.12345"), CurrencyVO(" usd "))
        layer = self.create(total_cost=cost)
        self.assertIs(layer.cost_basis.total_cost, cost)
        self.assertEqual(cost.amount, Decimal("10.1235"))
        self.assertEqual(cost.currency, CurrencyVO("USD"))
        # Наличие валюты в справочнике проверит Application, а не Domain.
        self.assertEqual(
            self.create(
                total_cost=MoneyVO(Decimal(5), CurrencyVO("ZZZ"))
            ).cost_basis.total_cost.currency.value,
            "ZZZ",
        )

    def test_cost_basis_requires_positive_quantity_and_nominal_money(self) -> None:
        """Количество слоя строго положительно; примитивы не заменяют QuantityVO и MoneyVO."""
        for quantity, cost in (
            (QuantityVO(Decimal(0)), self.cost),
            (Decimal(5), self.cost),
            (None, self.cost),
            (QuantityVO(Decimal(5)), Decimal(250)),
            (QuantityVO(Decimal(5)), None),
        ):
            with (
                self.subTest(quantity=quantity, cost=cost),
                self.assertRaises(InvalidCostBasisError),
            ):
                CostBasisVO(quantity, cost)
        with self.assertRaises(InvalidCostBasisError):
            self.create(total_cost=250)

    def test_full_cost_is_preserved_when_unit_price_cannot_be_represented(self) -> None:
        """Стоимость трёх единиц не теряется из-за округления цены 1/3 или малого денежного остатка."""
        receipt = self.produce(self.f.posting(entries=(self.f.entry("3"),)))
        for amount in ("1.0000", "0.0001"):
            with self.subTest(amount=amount):
                cost = MoneyVO(Decimal(amount), CurrencyVO("UAH"))
                layer = self.create(receipt=receipt, total_cost=cost)
                self.assertEqual(layer.cost_basis.quantity, QuantityVO(Decimal(3)))
                self.assertEqual(layer.cost_basis.total_cost, cost)

    def test_cost_basis_and_layer_are_frozen(self) -> None:
        """Первоначальная стоимость и количество не редактируются присваиванием."""
        layer = self.create()
        with self.assertRaises(FrozenInstanceError):
            layer.cost_basis = self.create().cost_basis
        with self.assertRaises(FrozenInstanceError):
            layer.cost_basis.quantity = QuantityVO(Decimal(3))

    def test_source_vo_requires_nominal_identifiers(self) -> None:
        """Ссылки на источники не принимают raw UUID или ID другого вида."""
        source = self.create().source
        for changes in (
            dict(posting_id=uuid4()),
            dict(ledger_entry_id=StockPostingIdVO(uuid4())),
            dict(position_id="position"),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(source, **changes)

    def test_snapshot_rejects_raw_fields_zero_quantity_and_non_utc_dates(self) -> None:
        """Готовый снимок уже содержит UTC и номинальные данные без скрытой нормализации."""
        for changes in (
            dict(posting_id=uuid4()),
            dict(ledger_entry_id=StockPostingIdVO(uuid4())),
            dict(position_id=None),
            dict(inventory_item_id=uuid4()),
            dict(owner_id=uuid4()),
            dict(warehouse_id=None),
            dict(base_uom="KG"),
            dict(quantity=QuantityVO(Decimal(0))),
            dict(quantity=Decimal(5)),
            dict(received_at=self.f.time.replace(tzinfo=None)),
            dict(received_at=self.f.time.astimezone(timezone(timedelta(hours=3)))),
            dict(received_at="now"),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(self.receipt, **changes).ensure_valid()

    def test_layer_requires_specialized_receipt_snapshot(self) -> None:
        """Агрегат, общий снимок проведения и raw-словарь не заменяют контракт прихода."""
        for receipt in (None, self.posting, self.posting.snapshot(), {}):
            with self.subTest(receipt=receipt), self.assertRaises(InventoryError):
                self.create(receipt=receipt)
        with self.assertRaises(InventoryError):
            self.create(receipt=replace(self.receipt, quantity=QuantityVO(Decimal(0))))

    def test_unknown_and_raw_entry_ids_are_rejected(self) -> None:
        """Нельзя выбрать запись другого проведения или передать примитив вместо Ledger Entry ID."""
        for identifier in (
            StockLedgerEntryIdVO(uuid4()),
            uuid4(),
            None,
            self.posting.id,
        ):
            with self.subTest(identifier=identifier), self.assertRaises(InventoryError):
                self.produce(ledger_entry_id=identifier)

    def test_position_identity_and_uom_must_match_selected_entry(self) -> None:
        """У выбранной записи должна быть ровно соответствующая исходная позиция и единица."""
        for position in (
            self.f.second.snapshot(),
            replace(self.f.first.snapshot(), base_uom=UomCodeVO("L")),
            self.f.first,
            None,
        ):
            with self.subTest(position=position), self.assertRaises(InventoryError):
                self.produce(position=position)

    def test_location_must_match_position_and_provides_warehouse(self) -> None:
        """Склад выводится из локации позиции, а чужая локация не принимается."""
        for location in (self.f.second_location, None, self.f.warehouse):
            with self.subTest(location=location), self.assertRaises(InventoryError):
                self.produce(location=location)
        self.assertEqual(self.receipt.warehouse_id, self.f.first_location.warehouse_id)

    def test_inactive_receipt_location_does_not_invalidate_history(self) -> None:
        """Фиксация стоимости не является новым физическим движением в текущую активную ячейку."""
        receipt = self.produce(location=replace(self.f.first_location, is_active=False))
        self.assertEqual(
            self.create(receipt=receipt).source.position_id, self.f.first.id
        )

    def test_issue_and_internal_move_never_create_purchase_layer(self) -> None:
        """Расход и положительная сторона внутреннего перемещения не увеличивают закупочную стоимость повторно."""
        issue = self.f.posting(
            operation_type=StockOperationType.ISSUE, entries=(self.f.entry("-5"),)
        )
        with self.assertRaises(InventoryError):
            self.produce(issue)
        move = self.f.movement()
        incoming = next(
            entry for entry in move.entries if entry.quantity_delta.value > 0
        )
        with self.assertRaises(InventoryError):
            self.produce(
                move,
                ledger_entry_id=incoming.id,
                position=self.f.second.snapshot(),
                location=self.f.second_location,
            )

    def test_positive_adjustment_is_not_a_purchase_receipt(self) -> None:
        """Положительная корректировка требует отдельного стоимостного сценария."""
        adjustment = self.historical_posting(
            self.f.entry(), operation_type=StockOperationType.ADJUSTMENT
        )
        with self.assertRaises(InventoryError):
            self.produce(adjustment)

    def test_receipt_reversal_is_rejected(self) -> None:
        """Компенсация поступления не является новым закупочным слоем."""
        reversal = StockPosting.create_reversal(
            identifier=StockPostingIdVO(uuid4()),
            source=PostingSourceVO(StockExecutionIdVO(uuid4())),
            posted_at=self.at,
            original=self.posting.snapshot(),
            entry_ids=(StockLedgerEntryIdVO(uuid4()),),
            positions=(self.f.first.snapshot(),),
        )
        with self.assertRaises(InventoryError):
            self.produce(reversal)

    def test_positive_issue_reversal_is_also_rejected(self) -> None:
        """Даже положительный знак не делает компенсацию расхода закупочным приходом."""
        issue = self.f.posting(
            operation_type=StockOperationType.ISSUE, entries=(self.f.entry("-5"),)
        )
        reversal = StockPosting.create_reversal(
            identifier=StockPostingIdVO(uuid4()),
            source=PostingSourceVO(StockExecutionIdVO(uuid4())),
            posted_at=self.at,
            original=issue.snapshot(),
            entry_ids=(StockLedgerEntryIdVO(uuid4()),),
            positions=(self.f.first.snapshot(),),
        )
        self.assertEqual(reversal.entries[0].quantity_delta.value, Decimal(5))
        with self.assertRaises(InventoryError):
            self.produce(reversal)

    def test_historical_conversion_is_not_replaced_with_current_factor(self) -> None:
        """Слой получает сохранённые 2 KG, не пересчитывая старые 1000 G современным коэффициентом."""
        conversion = QuantityConversionSnapshotVO(
            QuantityVO(Decimal(1000)), UomCodeVO("G"), Decimal(".002")
        )
        entry = StockLedgerEntry.restore(
            identifier=StockLedgerEntryIdVO(uuid4()),
            position_id=self.f.first.id,
            quantity_delta=StockDeltaVO(Decimal(2)),
            base_uom=UomCodeVO("KG"),
            conversion=conversion,
        )
        receipt = self.produce(self.historical_posting(entry))
        self.assertEqual(
            self.create(receipt=receipt).cost_basis.quantity, QuantityVO(Decimal(2))
        )

    def test_serial_receipt_requires_single_pcs(self) -> None:
        """Повторно проверяется единичность серийного движения по исходной позиции."""
        position = self.f.position(
            base_uom=UomCodeVO("PCS"),
            dimensions=replace(self.f.dimensions, serial_id=StockSerialIdVO(uuid4())),
        )
        single = self.f.entry("1", position)
        receipt = self.produce(
            self.f.posting(entries=(single,), positions=(position.snapshot(),)),
            position=position.snapshot(),
        )
        layer = self.create(receipt=receipt)
        self.assertEqual(layer.cost_basis.quantity, QuantityVO(Decimal(1)))
        malformed = self.historical_posting(self.f.entry("2", position))
        with self.assertRaises(InventoryError):
            self.produce(malformed, position=position.snapshot())

    def test_lot_receipts_are_separate_by_ledger_entry_without_fresh_expiry_check(
        self,
    ) -> None:
        """Цена привязывается к исходной записи партии без повторной проверки её актуальных сроков."""
        position = self.f.position(
            dimensions=replace(self.f.dimensions, lot_id=StockLotIdVO(uuid4()))
        )
        posting = self.f.posting(
            entries=(self.f.entry("5", position),), positions=(position.snapshot(),)
        )
        layer = self.create(receipt=self.produce(posting, position=position.snapshot()))
        self.assertEqual(layer.source.position_id, position.id)

    def test_creation_time_is_normalized_and_not_before_receipt(self) -> None:
        """Регистрация допускает равное время и aware-смещение, но не более ранний или наивный момент."""
        equal = self.create(created_at=self.receipt.received_at)
        self.assertEqual(equal.created_at, equal.received_at)
        offset = self.create(
            created_at=self.at.astimezone(timezone(timedelta(hours=2)))
        )
        self.assertEqual(offset.created_at, self.at)
        for created in (
            self.f.time - timedelta(seconds=1),
            self.at.replace(tzinfo=None),
            "now",
            None,
        ):
            with (
                self.subTest(created=created),
                self.assertRaises(ValuationLayerTimeError),
            ):
                self.create(created_at=created)

    def test_restore_preserves_history_without_source_or_current_settings(self) -> None:
        """Полный собственный состав достаточен для восстановления слоя."""
        layer = self.create()
        restored = self.restore(layer)
        self.assertEqual(restored, layer)
        self.assertIs(restored.cost_basis, layer.cost_basis)
        self.assertIs(restored.source, layer.source)
        self.assertEqual(
            self.restore(
                layer,
                received_at=layer.received_at.astimezone(timezone(timedelta(hours=2))),
            ),
            layer,
        )

    def test_restore_rejects_wrong_types_and_inverted_time(self) -> None:
        """Аннотации не заменяют проверки идентификаторов, основания стоимости и дат корня."""
        layer = self.create()
        for changes in (
            dict(identifier=uuid4()),
            dict(source=None),
            dict(inventory_item_id=uuid4()),
            dict(owner_id=None),
            dict(warehouse_id=uuid4()),
            dict(base_uom="KG"),
            dict(cost_basis=self.cost),
            dict(received_at=self.at + timedelta(seconds=1)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.restore(layer, **changes)

    def test_invalid_finite_values_cannot_be_hidden_inside_cost_basis(self) -> None:
        """Повторная проверка корня отклоняет повреждённый вложенный VO после обхода его конструктора."""
        quantity = object.__new__(QuantityVO)
        object.__setattr__(quantity, "value", Decimal("NaN"))
        basis = object.__new__(CostBasisVO)
        object.__setattr__(basis, "quantity", quantity)
        object.__setattr__(basis, "total_cost", self.cost)
        with self.assertRaises(InventoryError):
            self.restore(self.create(), cost_basis=basis)
        money = object.__new__(MoneyVO)
        object.__setattr__(money, "amount", Decimal("Infinity"))
        object.__setattr__(money, "currency", CurrencyVO("UAH"))
        with self.assertRaises(InvalidCostBasisError):
            CostBasisVO(QuantityVO(Decimal(1)), money)

    def test_noncanonical_saved_money_is_not_silently_rounded_again(self) -> None:
        """Восстановление не переписывает повреждённую историческую точность стоимости."""
        money = object.__new__(MoneyVO)
        object.__setattr__(money, "amount", Decimal("1.00001"))
        object.__setattr__(money, "currency", CurrencyVO("UAH"))
        with self.assertRaises(InvalidCostBasisError):
            CostBasisVO(QuantityVO(Decimal(1)), money)

    def test_small_decimal_context_does_not_round_quantity_or_cost(self) -> None:
        """Фиксация не умножает и не делит исторические значения во внешнем Decimal context."""
        posting = self.f.posting(entries=(self.f.entry("123.456789"),))
        receipt = self.produce(posting)
        cost = MoneyVO(Decimal("9876.5432"), CurrencyVO("EUR"))
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            layer = self.create(receipt=receipt, total_cost=cost)
            restored = self.restore(layer)
        self.assertEqual(restored.cost_basis.quantity.value, Decimal("123.456789"))
        self.assertEqual(restored.cost_basis.total_cost.amount, Decimal("9876.5432"))


if __name__ == "__main__":
    unittest.main()
