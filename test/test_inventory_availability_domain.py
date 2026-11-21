"""Пригодность физического остатка к резервированию без изменения остатков и создания резервов."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from itertools import permutations
from uuid import uuid4

from src.modules.inventory.domain.error import (
    DuplicatePositiveSerialStockError,
    ExpirationDateNotAllowedError,
    ExpirationDateRequiredError,
    InvalidStockAvailabilityContextError,
    QuantityStepError,
    StockQuantityArithmeticError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemAvailabilitySnapshotError,
    InvalidInventoryItemValueError,
    InvalidTrackingConfigurationError,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_availability import (
    StockAvailabilityPolicy,
)
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.error import (
    InvalidSerialStockQuantityError,
    InvalidStockPositionAvailabilitySnapshotError,
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
    InvalidStockSerialValueError,
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
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockAvailabilityDomainTests(unittest.TestCase):
    """Проверяет область расчёта, пригодность позиций, календарные границы и точную сумму."""

    def setUp(self) -> None:
        """Создаёт активный склад, адрес и товар с явным владельцем и датой оценки."""
        self.as_of = date(2026, 11, 4)
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()), self.warehouse.id, LocationType.STORAGE, True
        )
        self.owner = StockOwnerIdVO(uuid4())
        self.configure()

    def configure(
        self,
        mode: TrackingMode = TrackingMode.NONE,
        expiration: ExpirationMode = ExpirationMode.NONE,
    ) -> None:
        """Готовит реальный товар, партию и экземпляр для выбранной матрицы настроек."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("ITEM"),
            base_uom=UomCodeVO("PCS" if mode.requires_serial else "KG"),
            quantity_rules=QuantityRulesVO(
                Decimal(1) if mode.requires_serial else Decimal("0.05")
            ),
            tracking_mode=mode,
            expiration_mode=expiration,
        )
        dates = StockDatesVO(
            expires_on=self.as_of if expiration.controls_expiration else None
        )
        self.lot = (
            StockLot.restore(
                identifier=StockLotIdVO(uuid4()),
                inventory_item_id=self.item.id,
                number=LotNumberVO("LOT"),
                dates=dates,
            )
            if mode in (TrackingMode.LOT, TrackingMode.LOT_AND_SERIAL)
            else None
        )
        self.serial = (
            StockSerial.restore(
                identifier=StockSerialIdVO(uuid4()),
                inventory_item_id=self.item.id,
                number=SerialNumberVO("SN"),
                lot_id=self.lot.id if self.lot else None,
            )
            if mode.requires_serial
            else None
        )
        self.position = self.make_position("1" if mode.requires_serial else "10")

    def make_position(
        self,
        quantity: str,
        *,
        location: StockLocationSnapshot | None = None,
        status: StockStatus = StockStatus.SELLABLE,
    ) -> StockPosition:
        """Восстанавливает историческую позицию с текущими идентичностями прослеживаемости."""
        return StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=StockDimensionsVO(
                self.item.id,
                (self.location if location is None else location).id,
                self.owner,
                self.lot.id if self.lot else None,
                self.serial.id if self.serial else None,
                status,
            ),
            base_uom=self.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(quantity)),
            version=7,
        )

    def calculate(self, **changes: object) -> QuantityVO:
        """Передаёт ровно участвующие специализированные снимки в чистую Policy."""
        arguments = (
            dict(
                inventory_item=self.item.availability_snapshot(),
                warehouse=self.warehouse,
                owner_id=self.owner,
                as_of=self.as_of,
                positions=(self.position.availability_snapshot(),),
                locations=(self.location,),
                lots=(self.lot.snapshot(),) if self.lot else (),
                serials=(self.serial.snapshot(),) if self.serial else (),
            )
            | changes
        )
        return StockAvailabilityPolicy.calculate_eligible_quantity(**arguments)

    def set_dates(self, dates: StockDatesVO) -> None:
        """Меняет источник дат фикстуры без копирования партийных дат в экземпляр."""
        if self.lot is not None:
            self.lot = replace(self.lot, dates=dates)
        else:
            raise AssertionError("Даты существуют только у партии.")

    def test_snapshot_getters_are_minimal_frozen_and_validate_originals(self) -> None:
        """Три геттера не раскрывают коллекции или версии и проверяют исходное состояние корней."""
        self.configure(TrackingMode.SERIAL)
        for snapshot, fields in (
            (
                self.item.availability_snapshot(),
                {
                    "inventory_item_id",
                    "base_uom",
                    "quantity_rules",
                    "tracking_mode",
                    "expiration_mode",
                },
            ),
            (
                self.position.availability_snapshot(),
                {"id", "dimensions", "base_uom", "on_hand_qty"},
            ),
            (
                self.serial.snapshot(),
                {"id", "inventory_item_id", "lot_id"},
            ),
        ):
            self.assertEqual(set(snapshot.__dataclass_fields__), fields)
            snapshot.ensure_valid()
            name = next(iter(fields))
            with self.assertRaises(FrozenInstanceError):
                setattr(snapshot, name, None)
        with self.assertRaises(InvalidInventoryItemValueError):
            replace(self.item, sku="ITEM").availability_snapshot()
        with self.assertRaises(InvalidStockPositionValueError):
            replace(self.position, version=True).availability_snapshot()
        with self.assertRaises(InvalidStockSerialValueError):
            replace(self.serial, number="SN").snapshot()

    def test_empty_input_returns_typed_zero(self) -> None:
        """Пустой корректный набор даёт ноль даже для неактивного склада."""
        for active in (True, False):
            result = self.calculate(
                positions=(),
                locations=(),
                warehouse=replace(self.warehouse, is_active=active),
            )
            self.assertIsInstance(result, QuantityVO)
            self.assertEqual(result.value, Decimal(0))

    def test_every_tracking_and_expiration_configuration(self) -> None:
        """Все десять допустимых сочетаний используют текущую матрицу прослеживаемости."""
        for mode in TrackingMode:
            for expiration in ExpirationMode:
                if (
                    mode in (TrackingMode.NONE, TrackingMode.SERIAL)
                    and expiration.controls_expiration
                ):
                    continue
                with self.subTest(mode=mode, expiration=expiration):
                    self.configure(mode, expiration)
                    self.assertEqual(self.calculate(), self.position.on_hand_qty)

    def test_only_sellable_status_contributes(self) -> None:
        """QUARANTINE, DAMAGED и BLOCKED не меняют физический запас и дают нулевой вклад."""
        for status in StockStatus:
            position = self.make_position("10", status=status)
            result = self.calculate(positions=(position.availability_snapshot(),))
            self.assertEqual(
                result.value, Decimal(10 if status is StockStatus.SELLABLE else 0)
            )
            self.assertEqual(position.on_hand_qty.value, Decimal(10))

    def test_mixed_stock_has_twenty_physical_but_ten_required_or_fifteen_optional(
        self,
    ) -> None:
        """Смешанный набор из плана учитывает сроки и состояния независимо от порядка входных данных."""
        self.configure(TrackingMode.LOT, ExpirationMode.REQUIRED)
        shipping = replace(
            self.location,
            id=StockLocationIdVO(uuid4()),
            location_type=LocationType.SHIPPING,
        )
        expired_lot = replace(
            self.lot,
            id=StockLotIdVO(uuid4()),
            dates=StockDatesVO(expires_on=self.as_of - timedelta(days=1)),
        )
        expired_position = self.make_position("5")
        expired_position = replace(
            expired_position,
            dimensions=replace(expired_position.dimensions, lot_id=expired_lot.id),
        )
        positions = (
            self.make_position("10"),
            self.make_position("3", status=StockStatus.DAMAGED),
            self.make_position("2", location=shipping),
            expired_position,
        )
        self.assertEqual(
            sum(position.on_hand_qty.value for position in positions), Decimal(20)
        )
        for ordered in permutations(
            tuple(position.availability_snapshot() for position in positions)
        ):
            for lots in permutations((self.lot.snapshot(), expired_lot.snapshot())):
                self.assertEqual(
                    self.calculate(
                        positions=ordered,
                        locations=(shipping, self.location),
                        lots=lots,
                    ).value,
                    Decimal(10),
                )
        optional_item = replace(self.item, expiration_mode=ExpirationMode.OPTIONAL)
        self.assertEqual(
            self.calculate(
                inventory_item=optional_item.availability_snapshot(),
                positions=tuple(
                    position.availability_snapshot() for position in positions
                ),
                locations=(self.location, shipping),
                lots=(self.lot.snapshot(), expired_lot.snapshot()),
            ).value,
            Decimal(15),
        )

    def test_only_storage_location_contributes(self) -> None:
        """Приёмка, отгрузка, карантин и транзит не участвуют в первом правиле доступности."""
        for kind in LocationType:
            result = self.calculate(
                locations=(replace(self.location, location_type=kind),)
            )
            self.assertEqual(
                result.value, Decimal(10 if kind is LocationType.STORAGE else 0)
            )

    def test_inactive_warehouse_or_location_contributes_zero(self) -> None:
        """Неактивность корректного адреса или склада является фильтром, а не ошибкой истории."""
        for changes in (
            dict(warehouse=replace(self.warehouse, is_active=False)),
            dict(locations=(replace(self.location, is_active=False),)),
        ):
            self.assertEqual(self.calculate(**changes).value, Decimal(0))

    def test_required_expiration_includes_last_day_for_all_date_sources(self) -> None:
        """Вчера исключается, сегодня и завтра разрешены для партии и самостоятельного экземпляра."""
        for mode in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        ):
            self.configure(mode, ExpirationMode.REQUIRED)
            for offset in (-1, 0, 1):
                with self.subTest(mode=mode, offset=offset):
                    self.set_dates(
                        StockDatesVO(expires_on=self.as_of + timedelta(days=offset))
                    )
                    expected = (
                        self.position.on_hand_qty.value if offset >= 0 else Decimal(0)
                    )
                    self.assertEqual(self.calculate().value, expected)

    def test_optional_missing_and_expired_notes_never_filter_stock(self) -> None:
        """OPTIONAL допускает отсутствие срока и прошедшую дату-заметку без ограничений."""
        for mode in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        ):
            self.configure(mode, ExpirationMode.OPTIONAL)
            for expiry in (None, self.as_of - timedelta(days=1)):
                self.set_dates(StockDatesVO(expires_on=expiry))
                self.assertEqual(self.calculate(), self.position.on_hand_qty)

    def test_none_does_not_filter_by_manufacturing_date(self) -> None:
        """NONE не вводит скрытых ограничений по дате производства."""
        self.configure(TrackingMode.LOT)
        self.set_dates(StockDatesVO(manufactured_on=self.as_of + timedelta(days=100)))
        self.assertEqual(self.calculate().value, Decimal(10))

    def test_none_still_rejects_disallowed_expiration_data(self) -> None:
        """Игнорирование дат для доступности не отменяет запрета заполнять срок в NONE."""
        self.configure(TrackingMode.LOT)
        self.set_dates(StockDatesVO(expires_on=self.as_of))
        with self.assertRaises(ExpirationDateNotAllowedError):
            self.calculate()

    def test_required_missing_date_is_error_for_positive_even_excluded_stock(
        self,
    ) -> None:
        """Отсутствие обязательного срока не скрывается фильтрами состояния или активности."""
        for mode in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        ):
            self.configure(mode, ExpirationMode.REQUIRED)
            self.set_dates(StockDatesVO())
            for changes in (
                {},
                dict(warehouse=replace(self.warehouse, is_active=False)),
                dict(
                    positions=(
                        replace(
                            self.position.availability_snapshot(),
                            dimensions=replace(
                                self.position.dimensions,
                                stock_status=StockStatus.DAMAGED,
                            ),
                        ),
                    )
                ),
            ):
                with (
                    self.subTest(mode=mode, changes=changes),
                    self.assertRaises(ExpirationDateRequiredError),
                ):
                    self.calculate(**changes)

    def test_zero_position_does_not_require_expiration_date(self) -> None:
        """Нулевой остаток допускает неполную карточку, сохраняя обязательные ссылки."""
        for mode in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        ):
            self.configure(mode, ExpirationMode.REQUIRED)
            self.set_dates(StockDatesVO())
            zero = replace(self.position, on_hand_qty=QuantityVO(Decimal("-0.000")))
            self.assertEqual(
                self.calculate(positions=(zero.availability_snapshot(),)).value,
                Decimal(0),
            )

    def test_scope_and_date_require_typed_values(self) -> None:
        """Дата без времени и владелец передаются явно, включая расчёт пустого набора."""
        for value in (None, "2026-11-04", datetime(2026, 11, 4), True):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidStockAvailabilityContextError),
            ):
                self.calculate(as_of=value)
        with self.assertRaises(InvalidStockAvailabilityContextError):
            self.calculate(owner_id=uuid4())
        with self.assertRaises(InvalidStockAvailabilityContextError):
            self.calculate(positions=(), locations=(), as_of=None)

    def test_foreign_owner_item_warehouse_and_unit_are_errors(self) -> None:
        """Ошибочная область не превращается в молчаливое исключение позиции."""
        snapshot = self.position.availability_snapshot()
        for changes, error in (
            (
                dict(owner_id=StockOwnerIdVO(uuid4())),
                InvalidStockAvailabilityContextError,
            ),
            (
                dict(warehouse=replace(self.warehouse, id=WarehouseIdVO(uuid4()))),
                StockDimensionsMismatchError,
            ),
            (
                dict(
                    positions=(
                        replace(
                            snapshot,
                            dimensions=replace(
                                snapshot.dimensions,
                                inventory_item_id=InventoryItemIdVO(uuid4()),
                            ),
                        ),
                    )
                ),
                StockDimensionsMismatchError,
            ),
            (
                dict(positions=(replace(snapshot, base_uom=UomCodeVO("G")),)),
                StockPositionUomMismatchError,
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(error):
                self.calculate(**changes)

    def test_context_requires_tuples_and_exact_unique_snapshots(self) -> None:
        """Не принимает произвольные коллекции, лишние, отсутствующие или повторные адреса."""
        for field in ("positions", "locations", "lots", "serials"):
            with (
                self.subTest(field=field),
                self.assertRaises(InvalidStockAvailabilityContextError),
            ):
                self.calculate(**{field: []})
        extra = replace(self.location, id=StockLocationIdVO(uuid4()))
        for locations in ((), (self.location, self.location), (self.location, extra)):
            with self.assertRaises(InvalidStockAvailabilityContextError):
                self.calculate(locations=locations)

    def test_duplicate_position_id_or_dimensions_is_error(self) -> None:
        """Ни ID, ни полный ключ позиции нельзя посчитать дважды, даже при нулевом количестве."""
        for quantity in (Decimal(10), Decimal(0)):
            snapshot = replace(
                self.position.availability_snapshot(), on_hand_qty=QuantityVO(quantity)
            )
            for other in (
                snapshot,
                replace(snapshot, id=StockPositionIdVO(uuid4())),
                replace(
                    snapshot,
                    dimensions=replace(
                        snapshot.dimensions, stock_status=StockStatus.DAMAGED
                    ),
                ),
            ):
                with self.assertRaises(InvalidStockAvailabilityContextError):
                    self.calculate(positions=(snapshot, other))

    def test_lot_and_serial_context_is_exact_and_typed(self) -> None:
        """Отсутствующие, повторные и лишние снимки прослеживаемости не допускаются."""
        self.configure(TrackingMode.LOT_AND_SERIAL)
        lot = self.lot.snapshot()
        serial = self.serial.snapshot()
        for field, values, error in (
            ("lots", (), InvalidStockLotSnapshotError),
            ("serials", (), InvalidStockSerialSnapshotError),
            ("lots", (lot, lot), InvalidStockAvailabilityContextError),
            ("serials", (serial, serial), InvalidStockAvailabilityContextError),
            (
                "lots",
                (lot, replace(lot, id=StockLotIdVO(uuid4()))),
                InvalidStockAvailabilityContextError,
            ),
            (
                "serials",
                (serial, replace(serial, id=StockSerialIdVO(uuid4()))),
                InvalidStockAvailabilityContextError,
            ),
            (
                "lots",
                (replace(lot, inventory_item_id=InventoryItemIdVO(uuid4())),),
                StockDimensionsMismatchError,
            ),
            (
                "serials",
                (replace(serial, lot_id=StockLotIdVO(uuid4())),),
                StockDimensionsMismatchError,
            ),
        ):
            with self.subTest(field=field, values=values), self.assertRaises(error):
                self.calculate(**{field: values})

    def test_tracking_mode_requires_matching_position_dimensions(self) -> None:
        """LOT не может обходить обязательную партию и NONE не принимает лишнюю идентичность."""
        self.configure(TrackingMode.LOT)
        snapshot = self.position.availability_snapshot()
        with self.assertRaises(InvalidStockTrackingDimensionsError):
            self.calculate(
                positions=(
                    replace(
                        snapshot, dimensions=replace(snapshot.dimensions, lot_id=None)
                    ),
                ),
                lots=(),
            )
        self.configure()
        snapshot = self.position.availability_snapshot()
        with self.assertRaises(InvalidStockTrackingDimensionsError):
            self.calculate(
                positions=(
                    replace(
                        snapshot,
                        dimensions=replace(
                            snapshot.dimensions, lot_id=StockLotIdVO(uuid4())
                        ),
                    ),
                )
            )

    def test_positive_serial_in_multiple_positions_is_error_even_if_excluded(
        self,
    ) -> None:
        """Повтор положительного экземпляра выявляется во всём наборе, включая заблокированную позицию."""
        self.configure(TrackingMode.SERIAL)
        other_location = replace(
            self.location, id=StockLocationIdVO(uuid4()), is_active=False
        )
        other = self.make_position(
            "1", location=other_location, status=StockStatus.BLOCKED
        )
        with self.assertRaises(DuplicatePositiveSerialStockError):
            self.calculate(
                positions=(
                    self.position.availability_snapshot(),
                    other.availability_snapshot(),
                ),
                locations=(self.location, other_location),
            )
        zero = replace(other, on_hand_qty=QuantityVO(Decimal(0)))
        self.assertEqual(
            self.calculate(
                positions=(
                    self.position.availability_snapshot(),
                    zero.availability_snapshot(),
                ),
                locations=(self.location, other_location),
            ).value,
            Decimal(1),
        )

    def test_serial_quantity_is_zero_or_one_and_settings_require_pcs_step_one(
        self,
    ) -> None:
        """Потребитель повторно проверяет ограничения конкретной серии и настроек товара."""
        self.configure(TrackingMode.SERIAL)
        for value in ("0.5", "2"):
            snapshot = replace(
                self.position.availability_snapshot(),
                on_hand_qty=QuantityVO(Decimal(value)),
            )
            with self.assertRaises(InvalidSerialStockQuantityError):
                self.calculate(positions=(snapshot,))
        for changes in (
            dict(base_uom=UomCodeVO("KG")),
            dict(quantity_rules=QuantityRulesVO(Decimal(2))),
        ):
            with self.assertRaises(InvalidTrackingConfigurationError):
                self.calculate(
                    inventory_item=replace(self.item.availability_snapshot(), **changes)
                )

    def test_step_is_checked_even_for_excluded_positions(self) -> None:
        """Нельзя скрыть некратный физический остаток фильтром DAMAGED или неактивностью."""
        for status in (StockStatus.SELLABLE, StockStatus.DAMAGED):
            position = self.make_position("1.23", status=status)
            with self.assertRaises(QuantityStepError):
                self.calculate(positions=(position.availability_snapshot(),))

    def test_policy_rejects_entities_and_raw_values_instead_of_snapshots(self) -> None:
        """Ни полный корень, ни сырые значения не подменяют входной контракт расчёта."""
        for changes, error in (
            (
                dict(inventory_item=self.item),
                InvalidInventoryItemAvailabilitySnapshotError,
            ),
            (dict(inventory_item=None), InvalidInventoryItemAvailabilitySnapshotError),
            (dict(warehouse=None), InvalidWarehouseSnapshotError),
            (dict(locations=({},)), InvalidStockLocationSnapshotError),
            (
                dict(positions=(self.position,)),
                InvalidStockPositionAvailabilitySnapshotError,
            ),
            (
                dict(positions=(self.position.snapshot(),)),
                InvalidStockPositionAvailabilitySnapshotError,
            ),
        ):
            with self.assertRaises(error):
                self.calculate(**changes)
        self.configure(TrackingMode.LOT_AND_SERIAL)
        with self.assertRaises(InvalidStockLotSnapshotError):
            self.calculate(lots=(self.lot,))
        with self.assertRaises(InvalidStockSerialSnapshotError):
            self.calculate(serials=(self.serial,))

    def test_malformed_snapshots_are_revalidated_by_consumer(self) -> None:
        """Ручной dataclass-конструктор не позволяет обойти типы и совместимость снимков."""
        item = self.item.availability_snapshot()
        for changes in (
            dict(inventory_item_id=uuid4()),
            dict(base_uom="KG"),
            dict(quantity_rules=Decimal(1)),
            dict(tracking_mode="NONE"),
            dict(expiration_mode=None),
        ):
            with self.assertRaises(InvalidInventoryItemAvailabilitySnapshotError):
                self.calculate(inventory_item=replace(item, **changes))
        with self.assertRaises(InvalidTrackingConfigurationError):
            self.calculate(
                inventory_item=replace(item, expiration_mode=ExpirationMode.REQUIRED)
            )
        with self.assertRaises(UnknownUomError):
            self.calculate(inventory_item=replace(item, base_uom=UomCodeVO("BOX")))
        position = self.position.availability_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(dimensions={}),
            dict(base_uom="KG"),
            dict(on_hand_qty=Decimal(10)),
        ):
            with self.assertRaises(InvalidStockPositionAvailabilitySnapshotError):
                self.calculate(positions=(replace(position, **changes),))
        with self.assertRaises(InvalidWarehouseSnapshotError):
            self.calculate(warehouse=replace(self.warehouse, is_active=1))
        with self.assertRaises(InvalidStockLocationSnapshotError):
            self.calculate(locations=(replace(self.location, location_type="STORAGE"),))
        self.configure(TrackingMode.LOT_AND_SERIAL)
        with self.assertRaises(InvalidStockLotSnapshotError):
            self.calculate(lots=(replace(self.lot.snapshot(), dates=None),))
        with self.assertRaises(InvalidStockSerialSnapshotError):
            self.calculate(serials=(replace(self.serial.snapshot(), lot_id="LOT"),))
        self.configure(TrackingMode.SERIAL)
        with self.assertRaises(InvalidStockSerialSnapshotError):
            self.calculate(
                serials=(replace(self.serial.snapshot(), inventory_item_id=uuid4()),)
            )

    def test_exact_sum_is_independent_of_order_and_external_decimal_context(
        self,
    ) -> None:
        """Сумма точна при враждебном контексте и любом порядке позиций и адресов."""
        other_location = replace(self.location, id=StockLocationIdVO(uuid4()))
        first = self.make_position("12345678901234567890.10")
        second = self.make_position("0.05", location=other_location)
        expected = Decimal("12345678901234567890.15")
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            for positions in permutations(
                (first.availability_snapshot(), second.availability_snapshot())
            ):
                for locations in permutations((self.location, other_location)):
                    self.assertEqual(
                        self.calculate(positions=positions, locations=locations).value,
                        expected,
                    )
            self.assertFalse(any(context.flags.values()))

    def test_unrepresentable_sum_raises_controlled_domain_error(self) -> None:
        """Защитный предел точной арифметики не приводит к молчаливому округлению."""
        other_location = replace(self.location, id=StockLocationIdVO(uuid4()))
        large = self.make_position("1E+1000001")
        small = self.make_position("1", location=other_location)
        with self.assertRaises(StockQuantityArithmeticError):
            self.calculate(
                positions=(
                    large.availability_snapshot(),
                    small.availability_snapshot(),
                ),
                locations=(self.location, other_location),
            )

    def test_calculation_never_changes_roots_or_snapshots(self) -> None:
        """Успех и отказ сохраняют исходные количество, версию, даты и настройки."""
        self.configure(TrackingMode.LOT, ExpirationMode.REQUIRED)
        before = (self.position, self.item, self.lot)
        snapshots = (
            self.position.availability_snapshot(),
            self.item.availability_snapshot(),
            self.lot.snapshot(),
        )
        self.assertEqual(self.calculate().value, Decimal(10))
        with self.assertRaises(InvalidStockAvailabilityContextError):
            self.calculate(owner_id=StockOwnerIdVO(uuid4()))
        self.assertEqual((self.position, self.item, self.lot), before)
        self.assertEqual(
            (
                self.position.availability_snapshot(),
                self.item.availability_snapshot(),
                self.lot.snapshot(),
            ),
            snapshots,
        )
        self.assertEqual(
            (self.position.on_hand_qty.value, self.position.version), (Decimal(10), 7)
        )


if __name__ == "__main__":
    unittest.main()
