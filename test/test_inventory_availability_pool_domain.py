"""Жизненный цикл общего мягкого резерва и дефицита без изменения физических позиций."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from src.modules.inventory.domain.availability_pool.aggregate import AvailabilityPool
from src.modules.inventory.domain.availability_pool.error import (
    AvailabilityAssessmentDateError,
    AvailabilityPoolContextMismatchError,
    AvailabilityPoolUomMismatchError,
    AvailabilityPoolVersionConflictError,
    ExcessiveReservationReleaseError,
    ExcessiveReservationConsumptionError,
    InsufficientAvailableStockError,
    InvalidAvailabilityPoolKeyError,
    InvalidAvailabilityPoolValueError,
    InvalidReservationQuantityError,
)
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.error import (
    ExpirationDateRequiredError,
    ExpirationDateRequiredError,
    InvalidQuantityError,
    InvalidStockAvailabilityContextError,
    QuantityStepError,
    StockQuantityArithmeticError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemAvailabilitySnapshotError,
    InvalidInventoryItemStockSnapshotError,
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
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.error import (
    StockDimensionsMismatchError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
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


class AvailabilityPoolDomainTests(unittest.TestCase):
    """Проверяет общий резерв, повторный расчёт пригодности и неизменяемость состояния."""

    def setUp(self) -> None:
        """Готовит одну область учёта, действительный физический запас и явную дату оценки."""
        self.day = date(2026, 11, 4)
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
        """Создаёт реальные карточки товара, партии и экземпляра выбранного режима."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("POOL-ITEM"),
            base_uom=UomCodeVO("PCS" if mode.requires_serial else "KG"),
            quantity_rules=QuantityRulesVO(
                Decimal(1) if mode.requires_serial else Decimal("0.05")
            ),
            tracking_mode=mode,
            expiration_mode=expiration,
        )
        dates = StockDatesVO(
            expires_on=self.day if expiration.controls_expiration else None
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
        self.key = AvailabilityPoolKeyVO(self.item.id, self.warehouse.id, self.owner)
        self.position = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=StockDimensionsVO(
                self.item.id,
                self.location.id,
                self.owner,
                self.lot.id if self.lot else None,
                self.serial.id if self.serial else None,
                StockStatus.SELLABLE,
            ),
            base_uom=self.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(1) if mode.requires_serial else Decimal(10)),
            version=7,
        )

    def context(self) -> dict[str, object]:
        """Возвращает полные минимальные снимки для расчёта пригодности данного пула."""
        return dict(
            inventory_item=self.item.availability_snapshot(),
            warehouse=self.warehouse,
            as_of=self.day,
            positions=(self.position.availability_snapshot(),),
            locations=(self.location,),
            lots=(self.lot.snapshot(),) if self.lot else (),
            serials=(self.serial.snapshot(),) if self.serial else (),
        )

    def create(self, **changes: object) -> AvailabilityPool:
        """Создаёт пул по физическим снимкам без передачи сырого пригодного количества."""
        return AvailabilityPool.create(
            **(
                dict(identifier=AvailabilityPoolIdVO(uuid4()), key=self.key)
                | self.context()
                | changes
            )
        )

    def restore(self, **changes: object) -> AvailabilityPool:
        """Восстанавливает полный исторический состав без применения текущих правил."""
        return AvailabilityPool.restore(
            **(
                dict(
                    identifier=AvailabilityPoolIdVO(uuid4()),
                    key=self.key,
                    base_uom=self.item.base_uom,
                    eligible_qty=QuantityVO(Decimal(10)),
                    reserved_qty=QuantityVO(Decimal(0)),
                    assessed_on=self.day,
                    version=0,
                )
                | changes
            )
        )

    def reserve(
        self, pool: AvailabilityPool, amount: str = "7", **changes: object
    ) -> AvailabilityPool:
        """Резервирует положительное количество по ожидаемой версии и текущим снимкам."""
        return pool.reserve(
            **(
                dict(
                    quantity=QuantityVO(Decimal(amount)), expected_version=pool.version
                )
                | self.context()
                | changes
            )
        )

    def refresh(self, pool: AvailabilityPool, **changes: object) -> AvailabilityPool:
        """Повторно рассчитывает пригодность с явной ожидаемой версией."""
        return pool.refresh_eligible_quantity(
            **(dict(expected_version=pool.version) | self.context() | changes)
        )

    def consume(
        self, pool: AvailabilityPool, amount: str = "4", **changes: object
    ) -> AvailabilityPool:
        """Погашает общий резерв с пересчётом переданных физических снимков после расхода."""
        return pool.consume_reserved(
            **(
                dict(
                    quantity=QuantityVO(Decimal(amount)), expected_version=pool.version
                )
                | self.context()
                | changes
            )
        )

    def release(
        self, pool: AvailabilityPool, amount: str = "3", **changes: object
    ) -> AvailabilityPool:
        """Освобождает общий резерв без чтения физического контекста или даты."""
        return pool.release(
            **(
                dict(
                    quantity=QuantityVO(Decimal(amount)),
                    expected_version=pool.version,
                    inventory_item=self.item.stock_snapshot(),
                )
                | changes
            )
        )

    def test_key_is_typed_immutable_and_defines_exact_scope(self) -> None:
        """Ключ объединяет ровно товар, склад и владельца и сравнивается по значениям."""
        self.assertEqual(
            self.key, AvailabilityPoolKeyVO(self.item.id, self.warehouse.id, self.owner)
        )
        self.assertEqual(len({self.key, replace(self.key)}), 1)
        for field, value in (
            ("inventory_item_id", uuid4()),
            ("inventory_item_id", self.warehouse.id),
            ("warehouse_id", self.item.id),
            ("owner_id", None),
        ):
            with (
                self.subTest(field=field),
                self.assertRaises(InvalidAvailabilityPoolKeyError),
            ):
                replace(self.key, **{field: value})
        with self.assertRaises(FrozenInstanceError):
            self.key.owner_id = StockOwnerIdVO(uuid4())

    def test_create_calculates_stock_with_zero_reserve_and_version(self) -> None:
        """Создание выводит единицу из товара и получает пригодный запас из существующей Policy."""
        pool = self.create()
        self.assertEqual(
            (pool.eligible_qty.value, pool.reserved_qty.value, pool.version),
            (Decimal(10), Decimal(0), 0),
        )
        self.assertEqual(pool.available_qty.value, Decimal(10))
        self.assertEqual(pool.deficit_qty.value, Decimal(0))
        self.assertIs(pool.key, self.key)
        self.assertIs(pool.base_uom, self.item.base_uom)
        self.assertEqual(pool.assessed_on, self.day)
        self.assertEqual(self.position.version, 7)

    def test_create_uses_empty_and_inactive_stock_rules(self) -> None:
        """Пустая область или неактивный склад дают валидный нулевой пул без резерва."""
        for changes in (
            dict(positions=(), locations=()),
            dict(warehouse=replace(self.warehouse, is_active=False)),
            dict(
                locations=(replace(self.location, location_type=LocationType.SHIPPING),)
            ),
        ):
            pool = self.create(**changes)
            self.assertEqual(
                (pool.eligible_qty.value, pool.available_qty.value, pool.version),
                (Decimal(0), Decimal(0), 0),
            )

    def test_create_binds_item_warehouse_and_owner_to_key(self) -> None:
        """Даже пустая выборка не позволяет подменить товар или склад в ключе."""
        for key in (
            replace(self.key, inventory_item_id=InventoryItemIdVO(uuid4())),
            replace(self.key, warehouse_id=WarehouseIdVO(uuid4())),
        ):
            with self.assertRaises(AvailabilityPoolContextMismatchError):
                self.create(key=key, positions=(), locations=())
        with self.assertRaises(InvalidStockAvailabilityContextError):
            self.create(key=replace(self.key, owner_id=StockOwnerIdVO(uuid4())))

    def test_restore_preserves_history_and_allows_deficit_without_context(self) -> None:
        """Восстановление не применяет текущий шаг, дату или активность к историческому составу."""
        pool = self.restore(
            eligible_qty=QuantityVO(Decimal("1.23")),
            reserved_qty=QuantityVO(Decimal("2.46")),
            assessed_on=date(2020, 1, 1),
            version=42,
        )
        self.assertEqual(pool.eligible_qty.value, Decimal("1.23"))
        self.assertEqual(pool.reserved_qty.value, Decimal("2.46"))
        self.assertEqual(pool.deficit_qty.value, Decimal("1.23"))
        self.assertEqual(pool.available_qty.value, Decimal(0))
        self.assertEqual((pool.assessed_on, pool.version), (date(2020, 1, 1), 42))

    def test_restore_rejects_invalid_own_values(self) -> None:
        """Сырые значения, datetime и bool вместо версии не подменяют собственный контракт."""
        for changes in (
            dict(identifier=uuid4()),
            dict(key={}),
            dict(base_uom="KG"),
            dict(eligible_qty=Decimal(10)),
            dict(reserved_qty=None),
            dict(assessed_on=datetime(2026, 11, 4)),
            dict(assessed_on=None),
            dict(version=-1),
            dict(version=True),
            dict(version=Decimal(0)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidAvailabilityPoolValueError),
            ):
                self.restore(**changes)
        with self.assertRaises(UnknownUomError):
            self.restore(base_uom=UomCodeVO("BOX"))

    def test_reserve_increases_only_counter_and_one_version(self) -> None:
        """Обычный резерв сохраняет ключ, единицу и все физические состояния."""
        pool = self.create()
        changed = self.reserve(pool)
        self.assertEqual(
            (
                changed.eligible_qty.value,
                changed.reserved_qty.value,
                changed.available_qty.value,
                changed.version,
            ),
            (Decimal(10), Decimal(7), Decimal(3), 1),
        )
        self.assertEqual((pool.reserved_qty.value, pool.version), (Decimal(0), 0))
        self.assertIs(changed.id, pool.id)
        self.assertIs(changed.key, pool.key)
        self.assertIs(changed.base_uom, pool.base_uom)
        self.assertEqual(
            (self.position.on_hand_qty.value, self.position.version), (Decimal(10), 7)
        )

    def test_reserve_all_available_is_allowed_and_excess_is_not_partial(self) -> None:
        """Резерв ровно остатка допустим; превышение отклоняется без частичного результата."""
        reserved = self.reserve(self.create())
        with self.assertRaises(InsufficientAvailableStockError):
            self.reserve(reserved, "4")
        full = self.reserve(reserved, "3")
        self.assertEqual(
            (full.reserved_qty.value, full.available_qty.value),
            (Decimal(10), Decimal(0)),
        )
        with self.assertRaises(InsufficientAvailableStockError):
            self.reserve(full, "0.05")
        self.assertEqual(reserved.reserved_qty.value, Decimal(7))

    def test_reserve_recalculates_lower_and_higher_stock_before_check(self) -> None:
        """Сохранённая пригодность не используется как доказательство актуального запаса."""
        pool = self.create()
        lower = replace(
            self.position.availability_snapshot(), on_hand_qty=QuantityVO(Decimal(2))
        )
        with self.assertRaises(InsufficientAvailableStockError):
            self.reserve(
                pool, "3", positions=(lower,), as_of=self.day + timedelta(days=1)
            )
        self.assertEqual(
            (pool.eligible_qty.value, pool.assessed_on, pool.version),
            (Decimal(10), self.day, 0),
        )
        old = self.restore(eligible_qty=QuantityVO(Decimal(2)))
        changed = self.reserve(old, "7", as_of=self.day + timedelta(days=1))
        self.assertEqual(
            (changed.eligible_qty.value, changed.reserved_qty.value, changed.version),
            (Decimal(10), Decimal(7), 1),
        )
        self.assertEqual(changed.assessed_on, self.day + timedelta(days=1))

    def test_refresh_can_create_deficit_then_release_restores_free_stock(self) -> None:
        """Сценарий 10/0 → 10/7 → 5/7 → 5/4 сохраняет обязательства и показывает дефицит."""
        reserved = self.reserve(self.create())
        lower = replace(
            self.position.availability_snapshot(), on_hand_qty=QuantityVO(Decimal(5))
        )
        deficit = self.refresh(reserved, positions=(lower,))
        self.assertEqual(
            (
                deficit.eligible_qty.value,
                deficit.reserved_qty.value,
                deficit.available_qty.value,
                deficit.deficit_qty.value,
                deficit.version,
            ),
            (Decimal(5), Decimal(7), Decimal(0), Decimal(2), 2),
        )
        with self.assertRaises(InsufficientAvailableStockError):
            self.reserve(deficit, "1", positions=(lower,))
        released = self.release(deficit)
        self.assertEqual(
            (
                released.reserved_qty.value,
                released.available_qty.value,
                released.deficit_qty.value,
                released.version,
            ),
            (Decimal(4), Decimal(1), Decimal(0), 3),
        )
        self.assertEqual(
            (reserved.eligible_qty.value, reserved.reserved_qty.value),
            (Decimal(10), Decimal(7)),
        )

    def test_inactive_stock_can_be_refreshed_and_released_but_not_reserved(
        self,
    ) -> None:
        """Неактивность уменьшает пригодность до нуля, сохраняя возможность освободить весь резерв."""
        reserved = self.reserve(self.create())
        inactive = replace(self.warehouse, is_active=False)
        with self.assertRaises(InsufficientAvailableStockError):
            self.reserve(reserved, "1", warehouse=inactive)
        deficit = self.refresh(reserved, warehouse=inactive)
        released = self.release(deficit, "7")
        self.assertEqual(
            (
                deficit.eligible_qty.value,
                deficit.reserved_qty.value,
                deficit.deficit_qty.value,
            ),
            (Decimal(0), Decimal(7), Decimal(7)),
        )
        self.assertEqual(
            (released.available_qty.value, released.reserved_qty.value),
            (Decimal(0), Decimal(0)),
        )

    def test_required_expiration_refresh_preserves_reserve_and_optional_does_not_expire(
        self,
    ) -> None:
        """Переход календарного дня применяет существующую политику срока, не освобождая обязательства."""
        for expiration in (ExpirationMode.REQUIRED, ExpirationMode.OPTIONAL):
            self.configure(TrackingMode.LOT, expiration)
            self.lot = replace(self.lot, dates=StockDatesVO(expires_on=self.day))
            reserved = self.reserve(self.create())
            changed = self.refresh(reserved, as_of=self.day + timedelta(days=1))
            self.assertEqual(changed.reserved_qty.value, Decimal(7))
            self.assertEqual(
                changed.eligible_qty.value,
                Decimal(0 if expiration.controls_expiration else 10),
            )
            self.assertEqual(changed.version, 2)
        self.configure(TrackingMode.LOT, ExpirationMode.REQUIRED)
        self.lot = replace(self.lot, dates=StockDatesVO())
        with self.assertRaises(ExpirationDateRequiredError):
            self.create()

    def test_refresh_same_day_and_next_day_version_semantics(self) -> None:
        """Равный результат того же дня не меняет версию; новый день или количество меняют один раз."""
        pool = self.create()
        self.assertIs(self.refresh(pool), pool)
        same_number = replace(
            self.position.availability_snapshot(),
            on_hand_qty=QuantityVO(Decimal("10.000")),
        )
        self.assertIs(self.refresh(pool, positions=(same_number,)), pool)
        next_day = self.refresh(pool, as_of=self.day + timedelta(days=1))
        self.assertEqual(
            (next_day.eligible_qty, next_day.version), (pool.eligible_qty, 1)
        )
        lower = replace(
            self.position.availability_snapshot(), on_hand_qty=QuantityVO(Decimal(5))
        )
        changed = self.refresh(pool, positions=(lower,))
        self.assertEqual(
            (changed.assessed_on, changed.eligible_qty.value, changed.version),
            (self.day, Decimal(5), 1),
        )

    def test_noop_refresh_still_validates_scope_context_and_rules(self) -> None:
        """Равное количество не позволяет обойти проверки версии, снимков и текущего шага."""
        pool = self.create()
        with self.assertRaises(InvalidStockAvailabilityContextError):
            self.refresh(pool, locations=(self.location, self.location))
        with self.assertRaises(AvailabilityPoolContextMismatchError):
            self.refresh(
                pool,
                inventory_item=replace(
                    self.item.availability_snapshot(),
                    inventory_item_id=InventoryItemIdVO(uuid4()),
                ),
            )

    def test_assessment_requires_calendar_date_and_does_not_move_backwards(
        self,
    ) -> None:
        """Пересчёт и новый резерв не принимают datetime, строки или прежний день."""
        pool = self.create()
        for value in (
            None,
            "2026-11-04",
            datetime(2026, 11, 4),
            self.day - timedelta(days=1),
        ):
            for operation in (self.reserve, self.refresh, self.consume):
                with (
                    self.subTest(value=value, operation=operation.__name__),
                    self.assertRaises(AvailabilityAssessmentDateError),
                ):
                    operation(pool, as_of=value)
        with self.assertRaises(InvalidAvailabilityPoolValueError):
            self.create(as_of=datetime(2026, 11, 4))

    def test_all_transitions_require_strict_expected_version(self) -> None:
        """Bool, отрицательные и нетипизированные версии отклоняются до перехода состояния."""
        pool = self.reserve(self.create())
        for operation in (self.reserve, self.release, self.refresh, self.consume):
            for value in (True, False, -1, None, "1", Decimal(1), 1.0):
                with (
                    self.subTest(operation=operation.__name__, value=value),
                    self.assertRaises(InvalidAvailabilityPoolValueError),
                ):
                    operation(pool, expected_version=value)
            for value in (0, 2):
                with self.assertRaises(AvailabilityPoolVersionConflictError):
                    operation(pool, expected_version=value)

    def test_stale_version_prevents_calculation_and_release(self) -> None:
        """Неподходящая версия отклоняется до расчёта пригодности или арифметики освобождения."""
        pool = self.reserve(self.create())
        with patch.object(
            StockAvailabilityPolicy,
            "calculate_eligible_quantity",
            side_effect=RuntimeError("Не считать"),
        ):
            for operation in (self.reserve, self.refresh, self.consume):
                with self.assertRaises(AvailabilityPoolVersionConflictError):
                    operation(pool, expected_version=0)
        with patch(
            "src.modules.inventory.domain.policy.quantity_arithmetic.QuantityArithmeticPolicy.subtract",
            side_effect=RuntimeError("Не вычитать"),
        ):
            with self.assertRaises(AvailabilityPoolVersionConflictError):
                self.release(pool, expected_version=0)

    def test_old_version_is_rejected_on_updated_state_but_is_not_database_lock(
        self,
    ) -> None:
        """Две ветви одного исходного объекта допустимы; конфликт их записи должен обнаружить будущий SQL."""
        original = self.create()
        first = self.reserve(original, "7", expected_version=0)
        second = self.reserve(original, "7", expected_version=0)
        self.assertEqual(first.reserved_qty, second.reserved_qty)
        with self.assertRaises(AvailabilityPoolVersionConflictError):
            self.reserve(first, "1", expected_version=0)
        self.assertEqual(
            (original.reserved_qty.value, original.version), (Decimal(0), 0)
        )

    def test_reserve_and_release_reject_zero_raw_and_nonmultiple_quantities(
        self,
    ) -> None:
        """Операции не допускают нулевое количество и не округляют ввод пользователя."""
        pool = self.reserve(self.create())
        for operation in (self.reserve, self.release, self.consume):
            for value in ("0", "-0.000"):
                with self.assertRaises(InvalidReservationQuantityError):
                    operation(pool, value)
            for value in (Decimal(1), "1", None, 1):
                with self.assertRaises(InvalidQuantityError):
                    operation(pool, quantity=value)
            with self.assertRaises(QuantityStepError):
                operation(pool, "0.03")

    def test_release_is_partial_or_full_and_never_exceeds_counter(self) -> None:
        """Освобождение не меняет дату и пригодность и не делает резерв отрицательным."""
        pool = self.reserve(self.create())
        with self.assertRaises(ExcessiveReservationReleaseError):
            self.release(pool, "7.05")
        partial = self.release(pool, "2")
        full = self.release(partial, "5")
        self.assertEqual(
            (partial.reserved_qty.value, full.reserved_qty.value),
            (Decimal(5), Decimal(0)),
        )
        self.assertEqual(
            (full.assessed_on, full.eligible_qty, full.version),
            (pool.assessed_on, pool.eligible_qty, 3),
        )
        with self.assertRaises(ExcessiveReservationReleaseError):
            self.release(full, "0.05")

    def test_release_does_not_require_fresh_assessment_or_physical_context(
        self,
    ) -> None:
        """Исторический дефицит можно уменьшить без склада, даты или физических позиций."""
        pool = self.restore(
            eligible_qty=QuantityVO(Decimal(0)),
            reserved_qty=QuantityVO(Decimal(7)),
            assessed_on=date(2020, 1, 1),
        )
        released = self.release(pool)
        self.assertEqual(
            (
                released.reserved_qty.value,
                released.deficit_qty.value,
                released.assessed_on,
            ),
            (Decimal(4), Decimal(4), date(2020, 1, 1)),
        )

    def test_all_methods_check_current_item_and_immutable_unit(self) -> None:
        """Чужой товар и новая базовая единица не могут изменить исторические счётчики."""
        pool = self.reserve(self.create())
        for operation in (self.reserve, self.release, self.refresh, self.consume):
            item = (
                self.item.stock_snapshot()
                if operation == self.release
                else self.item.availability_snapshot()
            )
            for changes, error in (
                (
                    dict(inventory_item_id=InventoryItemIdVO(uuid4())),
                    AvailabilityPoolContextMismatchError,
                ),
                (dict(base_uom=UomCodeVO("G")), AvailabilityPoolUomMismatchError),
            ):
                with (
                    self.subTest(operation=operation.__name__, changes=changes),
                    self.assertRaises(error),
                ):
                    operation(pool, inventory_item=replace(item, **changes))
        for operation in (self.reserve, self.refresh, self.consume):
            with self.assertRaises(AvailabilityPoolContextMismatchError):
                operation(
                    pool, warehouse=replace(self.warehouse, id=WarehouseIdVO(uuid4()))
                )

    def test_current_rules_validate_stored_reserve_but_restore_keeps_history(
        self,
    ) -> None:
        """Собственное восстановление не проверяет текущий шаг; использование счётчика проверяет."""
        pool = self.restore(reserved_qty=QuantityVO(Decimal("1.23")))
        for operation in (self.reserve, self.release, self.refresh, self.consume):
            with self.assertRaises(QuantityStepError):
                (
                    operation(pool, "0.05")
                    if operation != self.refresh
                    else operation(pool)
                )

    def test_snapshot_types_and_full_physical_context_are_not_bypassed(self) -> None:
        """Создание и переходы используют специализированные снимки и существующую проверку измерений."""
        with self.assertRaises(InvalidInventoryItemAvailabilitySnapshotError):
            self.create(inventory_item=self.item)
        pool = self.reserve(self.create())
        for operation in (self.reserve, self.refresh, self.consume):
            with self.assertRaises(InvalidInventoryItemAvailabilitySnapshotError):
                operation(pool, inventory_item=self.item.stock_snapshot())
            with self.assertRaises(InvalidWarehouseSnapshotError):
                operation(pool, warehouse=None)
            position = self.position.availability_snapshot()
            wrong = replace(
                position,
                dimensions=replace(
                    position.dimensions, inventory_item_id=InventoryItemIdVO(uuid4())
                ),
            )
            with self.assertRaises(StockDimensionsMismatchError):
                operation(pool, positions=(wrong,))
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.release(pool, inventory_item=self.item.availability_snapshot())

    def test_serial_pool_can_hold_many_instances_but_only_integer_reserves(
        self,
    ) -> None:
        """Ограничение одной физической серии не ограничивает общий пул единицей."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            self.configure(mode)
            serials = tuple(
                replace(
                    self.serial,
                    id=StockSerialIdVO(uuid4()),
                    number=SerialNumberVO(str(number)),
                )
                for number in range(12)
            )
            positions = tuple(
                replace(
                    self.position,
                    id=StockPositionIdVO(uuid4()),
                    dimensions=replace(self.position.dimensions, serial_id=serial.id),
                )
                for serial in serials
            )
            context = dict(
                positions=tuple(
                    position.availability_snapshot() for position in positions
                ),
                serials=tuple(serial.snapshot() for serial in serials),
            )
            pool = self.create(**context)
            reserved = self.reserve(pool, "7", **context)
            self.assertEqual(
                (
                    reserved.eligible_qty.value,
                    reserved.reserved_qty.value,
                    reserved.available_qty.value,
                ),
                (Decimal(12), Decimal(7), Decimal(5)),
            )
            with self.assertRaises(QuantityStepError):
                self.reserve(reserved, "0.5", **context)
            with self.assertRaises(QuantityStepError):
                self.release(reserved, "0.5")

    def test_all_base_dimensions_follow_explicit_step(self) -> None:
        """Количество, масса, объём, длина и площадь используют единые явные правила количества."""
        for unit in ("PCS", "KG", "L", "M", "M2"):
            self.item = replace(self.item, base_uom=UomCodeVO(unit))
            self.position = replace(self.position, base_uom=self.item.base_uom)
            pool = self.reserve(self.create(), "1.25")
            self.assertEqual(
                (pool.base_uom.value, pool.reserved_qty.value), (unit, Decimal("1.25"))
            )

    def test_hostile_decimal_context_does_not_round_counters_or_properties(
        self,
    ) -> None:
        """Пересчёт, прибавление резерва и освобождение используют точную независимую арифметику."""
        self.position = replace(
            self.position, on_hand_qty=QuantityVO(Decimal("12345678901234567890.15"))
        )
        pool = self.restore(
            eligible_qty=self.position.on_hand_qty,
            reserved_qty=QuantityVO(Decimal("12345678901234567890.00")),
        )
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            reserved = self.reserve(pool, "0.05")
            self.assertEqual(
                reserved.reserved_qty.value, Decimal("12345678901234567890.05")
            )
            self.assertEqual(reserved.available_qty.value, Decimal("0.10"))
            self.assertEqual(reserved.deficit_qty.value, Decimal(0))
            released = self.release(reserved, "0.05")
            self.assertEqual(released.reserved_qty, pool.reserved_qty)
            self.assertFalse(any(context.flags.values()))

    def test_unrepresentable_difference_raises_controlled_domain_error(self) -> None:
        """Вычисляемые значения сохраняют технический предел точной арифметики."""
        pool = self.restore(
            eligible_qty=QuantityVO(Decimal("1E+1000001")),
            reserved_qty=QuantityVO(Decimal(1)),
        )
        with self.assertRaises(StockQuantityArithmeticError):
            _ = pool.available_qty
        deficit = replace(
            pool, eligible_qty=pool.reserved_qty, reserved_qty=pool.eligible_qty
        )
        with self.assertRaises(StockQuantityArithmeticError):
            _ = deficit.deficit_qty

    def test_direct_invalid_state_cannot_bypass_public_methods_or_properties(
        self,
    ) -> None:
        """Прямой dataclass-конструктор не обходит собственную проверку состава агрегата."""
        pool = self.reserve(self.create())
        for changes in (
            dict(key={}),
            dict(version=True),
            dict(eligible_qty=Decimal(10)),
            dict(reserved_qty=None),
            dict(assessed_on="2026-11-04"),
        ):
            malformed = replace(pool, **changes)
            for operation in (self.reserve, self.release, self.refresh, self.consume):
                with self.assertRaises(InvalidAvailabilityPoolValueError):
                    operation(malformed)
            for field in ("available_qty", "deficit_qty"):
                with self.assertRaises(InvalidAvailabilityPoolValueError):
                    getattr(malformed, field)

    def test_success_and_failure_leave_roots_and_frozen_pool_unchanged(self) -> None:
        """Состояние пула и физического запаса не меняется при успехе или отказе нового перехода."""
        pool = self.create()
        position_before = self.position.availability_snapshot()
        changed = self.reserve(pool)
        with self.assertRaises(InsufficientAvailableStockError):
            self.reserve(changed, "4")
        self.assertEqual((pool.reserved_qty.value, pool.version), (Decimal(0), 0))
        self.assertEqual((changed.reserved_qty.value, changed.version), (Decimal(7), 1))
        self.assertEqual(self.position.availability_snapshot(), position_before)
        with self.assertRaises(FrozenInstanceError):
            changed.reserved_qty = QuantityVO(Decimal(0))

    def test_consumption_recalculates_post_issue_stock_and_advances_once(self) -> None:
        """Погашение 4 из резерва 7 по остатку 6 даёт 6/3, не вычитая расход второй раз."""
        pool = self.reserve(self.create())
        after = replace(
            self.position.availability_snapshot(), on_hand_qty=QuantityVO(Decimal(6))
        )
        changed = self.consume(
            pool, positions=(after,), as_of=self.day + timedelta(days=1)
        )
        self.assertEqual(
            (
                changed.eligible_qty.value,
                changed.reserved_qty.value,
                changed.available_qty.value,
                changed.deficit_qty.value,
                changed.version,
            ),
            (Decimal(6), Decimal(3), Decimal(3), Decimal(0), 2),
        )
        self.assertEqual(changed.assessed_on, self.day + timedelta(days=1))
        self.assertEqual(
            (pool.eligible_qty.value, pool.reserved_qty.value, pool.version),
            (Decimal(10), Decimal(7), 1),
        )
        self.assertIs(changed.id, pool.id)
        self.assertIs(changed.key, pool.key)
        self.assertIs(changed.base_uom, pool.base_uom)

    def test_consumption_preserves_deficit_and_does_not_require_free_capacity(
        self,
    ) -> None:
        """Погашение уменьшает обязательства даже при нехватке пригодного запаса у остальных резервов."""
        pool = self.reserve(self.create())
        after = replace(
            self.position.availability_snapshot(), on_hand_qty=QuantityVO(Decimal(1))
        )
        changed = self.consume(pool, positions=(after,))
        self.assertEqual(
            (
                changed.reserved_qty.value,
                changed.eligible_qty.value,
                changed.available_qty.value,
                changed.deficit_qty.value,
            ),
            (Decimal(3), Decimal(1), Decimal(0), Decimal(2)),
        )
        inactive = self.consume(
            pool, warehouse=replace(self.warehouse, is_active=False)
        )
        self.assertEqual(
            (
                inactive.reserved_qty.value,
                inactive.eligible_qty.value,
                inactive.deficit_qty.value,
            ),
            (Decimal(3), Decimal(0), Decimal(3)),
        )

    def test_consumption_can_complete_hold_with_empty_post_issue_scope(self) -> None:
        """Нулевой остаток после полного расхода не мешает обнулить удержание."""
        pool = self.reserve(self.create())
        changed = self.consume(pool, "7", positions=(), locations=())
        self.assertEqual(
            (
                changed.eligible_qty.value,
                changed.reserved_qty.value,
                changed.available_qty.value,
                changed.version,
            ),
            (Decimal(0), Decimal(0), Decimal(0), 2),
        )
        with self.assertRaises(ExcessiveReservationConsumptionError):
            self.consume(pool, "7.05", positions=(), locations=())
        with self.assertRaises(ExcessiveReservationConsumptionError):
            self.consume(self.create(), "1")

    def test_consumption_checks_post_issue_context_even_for_complete_release(
        self,
    ) -> None:
        """Погашение не скрывает ошибки снимков, обязательной даты и текущего шага."""
        pool = self.reserve(self.create())
        with self.assertRaises(InvalidStockAvailabilityContextError):
            self.consume(pool, "7", locations=())
        with self.assertRaises(QuantityStepError):
            self.consume(
                pool,
                positions=(
                    replace(
                        self.position.availability_snapshot(),
                        on_hand_qty=QuantityVO(Decimal("1.23")),
                    ),
                ),
            )
        self.configure(TrackingMode.LOT, ExpirationMode.REQUIRED)
        pool = self.reserve(self.create())
        self.lot = replace(self.lot, dates=StockDatesVO())
        with self.assertRaises(ExpirationDateRequiredError):
            self.consume(pool)

    def test_consumption_recomputes_known_rules_without_deducting_quantity_from_total(
        self,
    ) -> None:
        """Пул принимает итоговый физический контекст; соответствие его расходу установит следующий срез."""
        pool = self.reserve(self.create())
        changed = self.consume(pool)
        self.assertEqual(
            (changed.eligible_qty.value, changed.reserved_qty.value),
            (Decimal(10), Decimal(3)),
        )
        self.assertEqual(self.position.on_hand_qty.value, Decimal(10))

    def test_serial_pool_consumption_uses_integer_step_and_zero_position(self) -> None:
        """После выдачи одного серийного экземпляра нулевая позиция и резерв дают нулевой пул."""
        self.configure(TrackingMode.SERIAL)
        pool = self.reserve(self.create(), "1")
        after = replace(
            self.position.availability_snapshot(), on_hand_qty=QuantityVO(Decimal(0))
        )
        with self.assertRaises(QuantityStepError):
            self.consume(pool, "0.5", positions=(after,))
        changed = self.consume(pool, "1", positions=(after,))
        self.assertEqual(
            (
                changed.eligible_qty.value,
                changed.reserved_qty.value,
                changed.available_qty.value,
            ),
            (Decimal(0), Decimal(0), Decimal(0)),
        )

    def test_consumption_hostile_decimal_context_is_exact(self) -> None:
        """Погашение и новый свободный остаток точно рассчитываются вне внешнего Decimal context."""
        pool = self.restore(
            eligible_qty=QuantityVO(Decimal("12345678901234567890.15")),
            reserved_qty=QuantityVO(Decimal("12345678901234567890.10")),
        )
        after = replace(
            self.position.availability_snapshot(),
            on_hand_qty=QuantityVO(Decimal("12345678901234567890.10")),
        )
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            changed = self.consume(pool, "0.05", positions=(after,))
            self.assertEqual(
                changed.reserved_qty.value, Decimal("12345678901234567890.05")
            )
            self.assertEqual(changed.available_qty.value, Decimal("0.05"))
            self.assertFalse(any(context.flags.values()))

    def test_consumption_unrepresentable_subtraction_leaves_source_unchanged(
        self,
    ) -> None:
        """Погашение не сохраняет округлённый резерв при недопустимом разрыве порядков."""
        pool = self.restore(
            eligible_qty=QuantityVO(Decimal("1E+1000001")),
            reserved_qty=QuantityVO(Decimal("1E+1000001")),
        )
        with self.assertRaises(StockQuantityArithmeticError):
            self.consume(pool, "1", positions=(), locations=())
        self.assertEqual(pool.reserved_qty.value, Decimal("1E+1000001"))


if __name__ == "__main__":
    unittest.main()
