"""Учётные измерения, физический остаток и проверка контекста StockPosition."""

import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.error import (
    NegativeStockQuantityError,
    QuantityStepError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
    InvalidTrackingConfigurationError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_dimensions import StockDimensionsPolicy
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.error import (
    InvalidSerialStockQuantityError,
    InvalidStockDimensionsError,
    InvalidStockPositionValueError,
    InvalidStockTrackingDimensionsError,
    StockDimensionsMismatchError,
    StockPositionUomMismatchError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class StockPositionDomainTests(unittest.TestCase):
    """Проверяет физическую позицию через реальные справочники и неизменяемые снимки."""

    def setUp(self) -> None:
        """Готовит склад, адрес и независимого владельца для весового товара."""
        self.warehouse = Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("MAIN"),
            name=WarehouseNameVO("Основной"),
        )
        self.location = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=self.warehouse.snapshot(),
            code=LocationCodeVO("A"),
            name=LocationNameVO("Адрес A"),
            location_type=LocationType.STORAGE,
        )
        self.owner_id = StockOwnerIdVO(uuid4())
        self.context = self.make_context()
        self.position = self.create_position()

    def make_context(self, mode: TrackingMode = TrackingMode.NONE) -> dict[str, object]:
        """Создаёт товар и исторические карточки прослеживаемости без внешних репозиториев."""
        item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("ITEM"),
            base_uom=UomCodeVO("PCS" if mode.requires_serial else "KG"),
            quantity_rules=QuantityRulesVO(
                Decimal("1" if mode.requires_serial else "0.05")
            ),
            tracking_mode=mode,
        )
        lot = (
            StockLot.restore(
                identifier=StockLotIdVO(uuid4()),
                inventory_item_id=item.id,
                number=LotNumberVO("LOT"),
                dates=StockDatesVO(),
            )
            if mode in (TrackingMode.LOT, TrackingMode.LOT_AND_SERIAL)
            else None
        )
        serial = (
            StockSerial.restore(
                identifier=StockSerialIdVO(uuid4()),
                inventory_item_id=item.id,
                number=SerialNumberVO("SN"),
                lot_id=lot.id if lot is not None else None,
            )
            if mode.requires_serial
            else None
        )
        dimensions = StockDimensionsVO(
            inventory_item_id=item.id,
            location_id=self.location.id,
            owner_id=self.owner_id,
            lot_id=lot.id if lot is not None else None,
            serial_id=serial.id if serial is not None else None,
            stock_status=StockStatus.SELLABLE,
        )
        return dict(
            dimensions=dimensions,
            inventory_item=item.stock_snapshot(),
            location=self.location.snapshot(),
            warehouse=self.warehouse.snapshot(),
            lot=lot.snapshot() if lot is not None else None,
            serial=serial.snapshot() if serial is not None else None,
        )

    def create_position(self, **changes: object) -> StockPosition:
        """Создаёт нулевую позицию с явно переопределённым контекстом."""
        return StockPosition.create(
            **(dict(identifier=StockPositionIdVO(uuid4())) | self.context | changes)
        )

    def restore_position(
        self, position: StockPosition | None = None, **changes: object
    ) -> StockPosition:
        """Восстанавливает полный собственный состав без текущих снимков."""
        original = self.position if position is None else position
        values = dict(
            identifier=original.id,
            dimensions=original.dimensions,
            base_uom=original.base_uom,
            on_hand_qty=original.on_hand_qty,
            version=original.version,
        )
        return StockPosition.restore(**(values | changes))

    def apply(
        self, value: str, position: StockPosition | None = None, **changes: object
    ) -> StockPosition:
        """Применяет дельту в базовой единице с явным текущим контекстом."""
        original = self.position if position is None else position
        context = {
            key: value for key, value in self.context.items() if key != "dimensions"
        }
        return original.apply_delta(StockDeltaVO(Decimal(value)), **(context | changes))

    def test_create_is_zero_version_zero_and_uses_item_base_unit(self) -> None:
        """Новая позиция не создаёт начальный физический остаток вне движения."""
        self.assertEqual(self.position.on_hand_qty.value, Decimal(0))
        self.assertEqual(self.position.version, 0)
        self.assertEqual(self.position.base_uom, UomCodeVO("KG"))
        self.assertIs(self.position.dimensions, self.context["dimensions"])

    def test_dimensions_are_typed_hashable_and_require_explicit_owner(self) -> None:
        """Ключ включает владельца и состояние, в том числе отсутствующие LOT и SERIAL."""
        dimensions = self.position.dimensions
        self.assertEqual(len({dimensions, replace(dimensions)}), 1)
        for changes in (
            dict(inventory_item_id=self.owner_id),
            dict(location_id=self.warehouse.id),
            dict(owner_id=None),
            dict(owner_id=self.warehouse.id),
            dict(owner_id=uuid4()),
            dict(lot_id=self.owner_id),
            dict(serial_id=StockLotIdVO(uuid4())),
            dict(stock_status="SELLABLE"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockDimensionsError),
            ):
                replace(dimensions, **changes)
        keys = {
            replace(dimensions, stock_status=status, owner_id=owner)
            for status in StockStatus
            for owner in (self.owner_id, StockOwnerIdVO(uuid4()))
        }
        self.assertEqual(len(keys), len(StockStatus) * 2)

    def test_position_and_owner_identifiers_are_separate_uuid_references(self) -> None:
        """Владелец не подменяется складом, товаром или идентичностью позиции."""
        value = uuid4()
        self.assertNotEqual(StockOwnerIdVO(value), WarehouseIdVO(value))
        self.assertNotEqual(StockPositionIdVO(value), InventoryItemIdVO(value))
        for factory in (StockOwnerIdVO, StockPositionIdVO):
            with self.subTest(factory=factory), self.assertRaises(EntityIdTypeError):
                factory(str(value))

    def test_tracking_matrix_is_checked_at_create_and_apply(self) -> None:
        """Проверяет все сочетания наличия LOT/SERIAL, включая повторную проверку восстановленной позиции."""
        full = self.make_context(TrackingMode.LOT_AND_SERIAL)
        for mode in TrackingMode:
            for has_lot in (False, True):
                for has_serial in (False, True):
                    context = full | dict(
                        inventory_item=replace(
                            full["inventory_item"], tracking_mode=mode
                        ),
                        dimensions=replace(
                            full["dimensions"],
                            lot_id=full["lot"].id if has_lot else None,
                            serial_id=full["serial"].id if has_serial else None,
                        ),
                        lot=full["lot"] if has_lot else None,
                        serial=(
                            replace(
                                full["serial"],
                                lot_id=(
                                    None
                                    if mode is TrackingMode.SERIAL
                                    else full["lot"].id
                                ),
                            )
                            if has_serial
                            else None
                        ),
                    )
                    allowed = (
                        has_lot
                        == (mode in (TrackingMode.LOT, TrackingMode.LOT_AND_SERIAL))
                        and has_serial == mode.requires_serial
                    )
                    with self.subTest(mode=mode, lot=has_lot, serial=has_serial):
                        if allowed:
                            position = self.create_position(**context)
                            changed = position.apply_delta(
                                StockDeltaVO(Decimal(1)),
                                **{
                                    key: value
                                    for key, value in context.items()
                                    if key != "dimensions"
                                },
                            )
                            self.assertEqual(changed.on_hand_qty.value, Decimal(1))
                        else:
                            with self.assertRaises(InvalidStockTrackingDimensionsError):
                                self.create_position(**context)
                            restored = self.restore_position(
                                dimensions=context["dimensions"],
                                base_uom=UomCodeVO("PCS"),
                            )
                            with self.assertRaises(InvalidStockTrackingDimensionsError):
                                restored.apply_delta(
                                    StockDeltaVO(Decimal(0)),
                                    **{
                                        key: value
                                        for key, value in context.items()
                                        if key != "dimensions"
                                    },
                                )

    def test_delta_changes_quantity_and_version_only(self) -> None:
        """Приход, частичный расход и обнуление сохраняют ключ и исходные экземпляры."""
        received = self.apply("1.2500")
        issued = self.apply("-0.25", received)
        empty = self.apply("-1", issued)
        for position, quantity, version in (
            (received, "1.25", 1),
            (issued, "1", 2),
            (empty, "0", 3),
        ):
            with self.subTest(version=version):
                self.assertEqual(position.on_hand_qty.value, Decimal(quantity))
                self.assertEqual(position.version, version)
                self.assertIs(position.id, self.position.id)
                self.assertIs(position.dimensions, self.position.dimensions)
                self.assertIs(position.base_uom, self.position.base_uom)
        self.assertEqual(self.position.on_hand_qty.value, Decimal(0))
        self.assertEqual(self.position.version, 0)

    def test_zero_delta_preserves_state_after_context_validation(self) -> None:
        """Нулевая дельта не увеличивает версию и не обходит проверку чужих ссылок."""
        received = self.apply("1.25")
        self.assertIs(self.apply("-0.000", received), received)
        with self.assertRaises(StockDimensionsMismatchError):
            self.apply(
                "0",
                received,
                inventory_item=replace(
                    self.context["inventory_item"],
                    inventory_item_id=InventoryItemIdVO(uuid4()),
                ),
            )

    def test_failed_quantity_change_leaves_quantity_and_version_unchanged(self) -> None:
        """Недостаток остатка и некратная дельта не публикуют частичное изменение."""
        received = self.apply("1.25")
        with self.assertRaises(NegativeStockQuantityError):
            self.apply("-1.30", received)
        with self.assertRaises(QuantityStepError):
            self.apply("0.001", received)
        self.assertEqual(received.on_hand_qty.value, Decimal("1.25"))
        self.assertEqual(received.version, 1)

    def test_serial_position_has_only_zero_or_one_piece(self) -> None:
        """Количество конкретного серийного ID ограничено независимо от целочисленного шага товара."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            context = self.make_context(mode)
            position = self.create_position(**context)
            kwargs = {
                key: value for key, value in context.items() if key != "dimensions"
            }
            received = position.apply_delta(StockDeltaVO(Decimal(1)), **kwargs)
            self.assertEqual(received.on_hand_qty.value, Decimal(1))
            self.assertEqual(
                received.apply_delta(
                    StockDeltaVO(Decimal(-1)), **kwargs
                ).on_hand_qty.value,
                Decimal(0),
            )
            with self.assertRaises(InvalidSerialStockQuantityError):
                position.apply_delta(StockDeltaVO(Decimal(2)), **kwargs)
            with self.assertRaises(InvalidSerialStockQuantityError):
                received.apply_delta(StockDeltaVO(Decimal(1)), **kwargs)
            with self.assertRaises(QuantityStepError):
                received.apply_delta(StockDeltaVO(Decimal("0.5")), **kwargs)
            for changes in (
                dict(on_hand_qty=QuantityVO(Decimal(2))),
                dict(on_hand_qty=QuantityVO(Decimal("0.5"))),
                dict(base_uom=UomCodeVO("KG")),
            ):
                with (
                    self.subTest(mode=mode, changes=changes),
                    self.assertRaises(InvalidSerialStockQuantityError),
                ):
                    self.restore_position(position, **changes)
            self.assertEqual(received.version, 1)

    def test_restore_preserves_full_state_without_current_snapshots(self) -> None:
        """Исторический остаток восстанавливается без загрузки справочников и сохраняет идентичность."""
        quantity = QuantityVO(Decimal("123.45"))
        restored = self.restore_position(on_hand_qty=quantity, version=7)
        self.assertIs(restored.id, self.position.id)
        self.assertIs(restored.dimensions, self.position.dimensions)
        self.assertIs(restored.on_hand_qty, quantity)
        self.assertEqual(restored.version, 7)
        self.assertEqual(self.apply("0.05", restored).version, 8)
        incompatible = self.restore_position(on_hand_qty=QuantityVO(Decimal("1.23")))
        with self.assertRaises(QuantityStepError):
            self.apply("0", incompatible)

    def test_base_unit_cannot_be_reinterpreted_even_for_zero_delta(self) -> None:
        """Другой известный код единицы не пересчитывает уже существующий остаток автоматически."""
        with self.assertRaises(StockPositionUomMismatchError):
            self.apply(
                "0",
                inventory_item=replace(
                    self.context["inventory_item"], base_uom=UomCodeVO("G")
                ),
            )
        with self.assertRaises(UnknownUomError):
            self.restore_position(base_uom=UomCodeVO("UNKNOWN"))

    def test_inactive_warehouse_and_location_do_not_erase_physical_quantity(
        self,
    ) -> None:
        """Проверка разрешения операции остаётся будущему проведению, а физический учёт сохраняется."""
        warehouse = self.warehouse.deactivate()
        location = self.location.deactivate(warehouse=warehouse.snapshot())
        context = self.context | dict(
            warehouse=warehouse.snapshot(), location=location.snapshot()
        )
        position = self.create_position(**context)
        changed = position.apply_delta(
            StockDeltaVO(Decimal("1.25")),
            **{key: value for key, value in context.items() if key != "dimensions"},
        )
        self.assertEqual(changed.on_hand_qty.value, Decimal("1.25"))
        self.assertEqual(self.restore_position(changed), changed)

    def test_foreign_item_location_warehouse_and_traceability_are_rejected(
        self,
    ) -> None:
        """Снимки должны совпадать с ключом, включая конкретную серию и её партию."""
        full = self.make_context(TrackingMode.LOT_AND_SERIAL)
        position = self.create_position(**full)
        for changes in (
            dict(
                inventory_item=replace(
                    full["inventory_item"], inventory_item_id=InventoryItemIdVO(uuid4())
                )
            ),
            dict(location=replace(full["location"], id=StockLocationIdVO(uuid4()))),
            dict(warehouse=replace(full["warehouse"], id=WarehouseIdVO(uuid4()))),
            dict(lot=replace(full["lot"], id=StockLotIdVO(uuid4()))),
            dict(
                lot=replace(full["lot"], inventory_item_id=InventoryItemIdVO(uuid4()))
            ),
            dict(serial=replace(full["serial"], id=StockSerialIdVO(uuid4()))),
            dict(
                serial=replace(
                    full["serial"], inventory_item_id=InventoryItemIdVO(uuid4())
                )
            ),
            dict(serial=replace(full["serial"], lot_id=StockLotIdVO(uuid4()))),
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(StockDimensionsMismatchError):
                    self.create_position(**(full | changes))
                with self.assertRaises(StockDimensionsMismatchError):
                    position.apply_delta(
                        StockDeltaVO(Decimal(0)),
                        **(
                            {
                                key: value
                                for key, value in full.items()
                                if key != "dimensions"
                            }
                            | changes
                        ),
                    )

    def test_extra_or_missing_traceability_snapshots_are_rejected(self) -> None:
        """Лишние сведения не игнорируются, а обязательные ID требуют соответствующего снимка."""
        full = self.make_context(TrackingMode.LOT_AND_SERIAL)
        for changes in (dict(lot=full["lot"]), dict(serial=full["serial"])):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockTrackingDimensionsError),
            ):
                self.create_position(**changes)
        for key, error in (
            ("lot", InvalidStockLotSnapshotError),
            ("serial", InvalidStockSerialSnapshotError),
        ):
            with self.subTest(key=key), self.assertRaises(error):
                self.create_position(**(full | {key: None}))

    def test_malformed_snapshots_are_domain_errors_at_create_and_apply(self) -> None:
        """Проверяются типы всех контрактов, включая настоящий bool и вложенные ссылки."""
        full = self.make_context(TrackingMode.LOT_AND_SERIAL)
        cases = (
            (dict(inventory_item=None), InvalidInventoryItemStockSnapshotError),
            (
                dict(inventory_item=replace(full["inventory_item"], base_uom="PCS")),
                InvalidInventoryItemStockSnapshotError,
            ),
            (
                dict(
                    inventory_item=replace(full["inventory_item"], quantity_rules=None)
                ),
                InvalidInventoryItemStockSnapshotError,
            ),
            (
                dict(
                    inventory_item=replace(
                        full["inventory_item"], tracking_mode="LOT_AND_SERIAL"
                    )
                ),
                InvalidInventoryItemStockSnapshotError,
            ),
            (dict(location=None), InvalidStockLocationSnapshotError),
            (
                dict(location=replace(full["location"], is_active=1)),
                InvalidStockLocationSnapshotError,
            ),
            (dict(warehouse=None), InvalidWarehouseSnapshotError),
            (
                dict(warehouse=replace(full["warehouse"], id=self.location.id)),
                InvalidWarehouseSnapshotError,
            ),
            (
                dict(lot=replace(full["lot"], id=self.owner_id)),
                InvalidStockLotSnapshotError,
            ),
            (dict(lot=replace(full["lot"], dates=None)), InvalidStockLotSnapshotError),
            (
                dict(serial=replace(full["serial"], id=self.owner_id)),
                InvalidStockSerialSnapshotError,
            ),
            (
                dict(serial=replace(full["serial"], lot_id=self.owner_id)),
                InvalidStockSerialSnapshotError,
            ),
        )
        position = self.create_position(**full)
        for changes, error in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(error):
                    self.create_position(**(full | changes))
                with self.assertRaises(error):
                    position.apply_delta(
                        StockDeltaVO(Decimal(0)),
                        **(
                            {
                                key: value
                                for key, value in full.items()
                                if key != "dimensions"
                            }
                            | changes
                        ),
                    )
        for changes in (
            dict(base_uom=UomCodeVO("KG")),
            dict(quantity_rules=QuantityRulesVO(Decimal("0.5"))),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidTrackingConfigurationError),
            ):
                self.create_position(
                    **(
                        full
                        | dict(
                            inventory_item=replace(full["inventory_item"], **changes)
                        )
                    )
                )

    def test_restore_and_creation_require_typed_own_state(self) -> None:
        """Сырые количества, чужие ID и отрицательные либо нецелые версии отклоняются."""
        for changes in (
            dict(identifier=None),
            dict(identifier=self.owner_id),
            dict(dimensions={}),
            dict(base_uom="KG"),
            dict(on_hand_qty=Decimal(1)),
            dict(on_hand_qty=StockDeltaVO(Decimal(1))),
            dict(version=-1),
            dict(version=True),
            dict(version=1.0),
            dict(version="1"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockPositionValueError),
            ):
                self.restore_position(**changes)
        with self.assertRaises(InvalidStockPositionValueError):
            self.create_position(identifier=self.owner_id)
        with self.assertRaises(InvalidStockDimensionsError):
            self.create_position(dimensions={})
        with self.assertRaises(InvalidStockDimensionsError):
            StockDimensionsPolicy.ensure_compatible(
                **(self.context | dict(dimensions=None))
            )

    def test_stock_snapshots_are_minimal_and_preserve_original_references(self) -> None:
        """Геттеры не передают корни и их коллекции, сохраняя типизированную идентичность."""
        item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("X"),
            base_uom=UomCodeVO("PCS"),
            quantity_rules=QuantityRulesVO(Decimal(1)),
            tracking_mode=TrackingMode.SERIAL,
        )
        snapshot = item.stock_snapshot()
        self.assertIs(snapshot.inventory_item_id, item.id)
        self.assertIs(snapshot.quantity_rules, item.quantity_rules)
        self.assertEqual(item.change_sku(SkuVO("Y")).stock_snapshot(), snapshot)
        serial = StockSerial.create(
            identifier=StockSerialIdVO(uuid4()),
            inventory_item=item.tracking_snapshot(),
            number=SerialNumberVO("SN"),
        )
        self.assertIs(serial.snapshot().id, serial.id)
        self.assertIs(serial.snapshot().inventory_item_id, item.id)
        self.assertIsNone(serial.snapshot().lot_id)

    def test_root_dimensions_and_snapshots_are_immutable(self) -> None:
        """Нельзя заменить остаток, версию, единицу или измерение в обход доменного перехода."""
        for obj, field, value in (
            (self.position, "on_hand_qty", QuantityVO(Decimal(1))),
            (self.position, "version", 5),
            (self.position, "base_uom", UomCodeVO("G")),
            (
                self.position,
                "dimensions",
                replace(self.position.dimensions, stock_status=StockStatus.BLOCKED),
            ),
            (self.position.dimensions, "owner_id", StockOwnerIdVO(uuid4())),
            (self.context["inventory_item"], "tracking_mode", TrackingMode.LOT),
        ):
            with self.subTest(field=field), self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)

    def test_invalid_direct_state_does_not_bypass_delta_validation(self) -> None:
        """Публичный переход повторно проверяет собственное состояние перед арифметикой."""
        invalid = StockPosition(
            self.position.id,
            self.position.dimensions,
            self.position.base_uom,
            self.position.on_hand_qty,
            True,
        )
        with self.assertRaises(InvalidStockPositionValueError):
            self.apply("0", invalid)
