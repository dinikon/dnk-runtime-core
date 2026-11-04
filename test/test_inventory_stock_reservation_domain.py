"""Мягкое удержание под обязательство и его согласование с общим пулом без хранения."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from src.modules.inventory.domain.availability_pool.aggregate import AvailabilityPool
from src.modules.inventory.domain.availability_pool.error import (
    InsufficientAvailableStockError,
    InvalidAvailabilityPoolReservationSnapshotError,
    InvalidAvailabilityPoolValueError,
)
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.error import (
    InvalidQuantityError,
    QuantityStepError,
    StockQuantityArithmeticError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
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
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_reservation.aggregate import StockReservation
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidReservationSourceError,
    InvalidStockReservationQuantityError,
    InvalidStockReservationValueError,
    StockReservationExpirationError,
    StockReservationConsumptionExceededError,
    StockReservationExpiredError,
    StockReservationItemMismatchError,
    StockReservationLimitExceededError,
    StockReservationReleaseExceededError,
    StockReservationStatusError,
    StockReservationTimeError,
    StockReservationUomMismatchError,
    StockReservationVersionConflictError,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockReservationDomainTests(unittest.TestCase):
    """Проверяет лимиты, статусы, календарное время, версии и границы двух агрегатов."""

    def setUp(self) -> None:
        """Готовит реальный товар, физическую позицию и общий пул одного склада и владельца."""
        self.time = datetime(2026, 11, 4, 10, tzinfo=UTC)
        self.deadline = self.time + timedelta(hours=1)
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("RESERVE-ITEM"),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()), self.warehouse.id, LocationType.STORAGE, True
        )
        self.owner = StockOwnerIdVO(uuid4())
        self.key = AvailabilityPoolKeyVO(self.item.id, self.warehouse.id, self.owner)
        self.position = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=StockDimensionsVO(
                self.item.id,
                self.location.id,
                self.owner,
                None,
                None,
                StockStatus.SELLABLE,
            ),
            base_uom=self.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(10)),
            version=7,
        )
        self.pool = AvailabilityPool.create(
            identifier=AvailabilityPoolIdVO(uuid4()),
            key=self.key,
            **self.pool_context(),
        )
        self.source = ReservationSourceVO("sales_order_line", "ORDER-1/1")

    def pool_context(self) -> dict[str, object]:
        """Возвращает текущие снимки и явно выбранный календарный день оценки пула."""
        return dict(
            inventory_item=self.item.availability_snapshot(),
            warehouse=self.warehouse,
            as_of=self.time.date(),
            positions=(self.position.availability_snapshot(),),
            locations=(self.location,),
        )

    def create(self, **changes: object) -> StockReservation:
        """Создаёт ожидание по привязке к пулу без изменения его общего счётчика."""
        return StockReservation.create(
            **(
                dict(
                    identifier=StockReservationIdVO(uuid4()),
                    pool=self.pool.reservation_snapshot(),
                    inventory_item=self.item.stock_snapshot(),
                    source_ref=self.source,
                    requested_qty=QuantityVO(Decimal(7)),
                    created_at=self.time,
                    expires_at=self.deadline,
                )
                | changes
            )
        )

    def restore(self, **changes: object) -> StockReservation:
        """Восстанавливает собственный исторический состав без текущих снимков."""
        return StockReservation.restore(
            **(
                dict(
                    identifier=StockReservationIdVO(uuid4()),
                    source_ref=self.source,
                    pool_id=self.pool.id,
                    key=self.key,
                    base_uom=self.item.base_uom,
                    requested_qty=QuantityVO(Decimal(7)),
                    reserved_qty=QuantityVO(Decimal(0)),
                    status=StockReservationStatus.PENDING,
                    consumed_qty=QuantityVO(Decimal(0)),
                    expires_at=self.deadline,
                    created_at=self.time,
                    updated_at=self.time,
                    version=0,
                )
                | changes
            )
        )

    def add(
        self, reservation: StockReservation, amount: str = "4", **changes: object
    ) -> StockReservation:
        """Регистрирует положительное увеличение по текущим правилам товара."""
        return reservation.add_reserved(
            **(
                dict(
                    quantity=QuantityVO(Decimal(amount)),
                    expected_version=reservation.version,
                    inventory_item=self.item.stock_snapshot(),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def release(
        self, reservation: StockReservation, amount: str = "2", **changes: object
    ) -> StockReservation:
        """Регистрирует положительное освобождение удержания конкретного обязательства."""
        return reservation.release(
            **(
                dict(
                    quantity=QuantityVO(Decimal(amount)),
                    expected_version=reservation.version,
                    inventory_item=self.item.stock_snapshot(),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def consume(
        self, reservation: StockReservation, amount: str = "4", **changes: object
    ) -> StockReservation:
        """Переносит удержание в использование по явным времени факта и времени регистрации."""
        return reservation.consume(
            **(
                dict(
                    quantity=QuantityVO(Decimal(amount)),
                    expected_version=reservation.version,
                    inventory_item=self.item.stock_snapshot(),
                    consumed_at=self.time,
                    updated_at=self.time,
                )
                | changes
            )
        )

    def close(
        self, reservation: StockReservation, **changes: object
    ) -> StockReservation:
        """Закрывает ожидание или удержание без чтения пула и товара."""
        return reservation.release_all(
            **(
                dict(expected_version=reservation.version, updated_at=self.time)
                | changes
            )
        )

    def expire(
        self, reservation: StockReservation, **changes: object
    ) -> StockReservation:
        """Явно закрывает обязательство на границе его срока действия."""
        return reservation.expire(
            **(
                dict(expected_version=reservation.version, updated_at=self.deadline)
                | changes
            )
        )

    def test_source_normalizes_edges_preserves_case_and_rejects_controls(self) -> None:
        """Ссылка обязательна, сохраняет регистр и ведущие нули без управляющих символов."""
        source = ReservationSourceVO(" SalesOrderLine ", " 001/AbC ")
        self.assertEqual(
            (source.system, source.reference), ("SalesOrderLine", "001/AbC")
        )
        self.assertNotEqual(source, ReservationSourceVO("salesorderline", "001/abc"))
        for field in ("system", "reference"):
            for value in (None, 1, "", "  ", "a\nb", "a\x00b", "a\u200bb"):
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaises(InvalidReservationSourceError),
                ):
                    replace(source, **{field: value})
        with self.assertRaises(FrozenInstanceError):
            source.reference = "OTHER"

    def test_pool_snapshot_is_minimal_frozen_and_checks_original(self) -> None:
        """Снимок передаёт только привязку без версии, свободного запаса и разрешения резервировать."""
        snapshot = self.pool.reservation_snapshot()
        self.assertEqual(set(snapshot.__dataclass_fields__), {"id", "key", "base_uom"})
        self.assertIs(snapshot.id, self.pool.id)
        self.assertIs(snapshot.key, self.pool.key)
        snapshot.ensure_valid()
        with self.assertRaises(FrozenInstanceError):
            snapshot.id = AvailabilityPoolIdVO(uuid4())
        with self.assertRaises(InvalidAvailabilityPoolValueError):
            replace(self.pool, version=True).reservation_snapshot()

    def test_create_is_pending_zero_and_derives_binding_without_changing_pool(
        self,
    ) -> None:
        """Создание сохраняет запрос, основание и область, оставляя общий резерв нулевым."""
        reservation = self.create()
        self.assertEqual(
            (reservation.status, reservation.reserved_qty.value, reservation.version),
            (StockReservationStatus.PENDING, Decimal(0), 0),
        )
        self.assertEqual(reservation.requested_qty.value, Decimal(7))
        self.assertIs(reservation.source_ref, self.source)
        self.assertIs(reservation.pool_id, self.pool.id)
        self.assertIs(reservation.key, self.key)
        self.assertIs(reservation.base_uom, self.item.base_uom)
        self.assertEqual(
            (reservation.created_at, reservation.updated_at, reservation.expires_at),
            (self.time, self.time, self.deadline),
        )
        self.assertEqual(
            (self.pool.reserved_qty.value, self.pool.version), (Decimal(0), 0)
        )

    def test_create_revalidates_pool_snapshot_and_item_binding(self) -> None:
        """Сырые значения, полный пул, чужой товар и новая единица не подменяют контракт."""
        for value in (None, self.pool, {}, Decimal(10)):
            with self.assertRaises(InvalidAvailabilityPoolReservationSnapshotError):
                self.create(pool=value)
        snapshot = self.pool.reservation_snapshot()
        for changes in (dict(id=uuid4()), dict(key={}), dict(base_uom="KG")):
            with self.assertRaises(InvalidAvailabilityPoolReservationSnapshotError):
                self.create(pool=replace(snapshot, **changes))
        with self.assertRaises(UnknownUomError):
            self.create(pool=replace(snapshot, base_uom=UomCodeVO("BOX")))
        with self.assertRaises(StockReservationItemMismatchError):
            self.create(
                inventory_item=replace(
                    self.item.stock_snapshot(),
                    inventory_item_id=InventoryItemIdVO(uuid4()),
                )
            )
        with self.assertRaises(StockReservationUomMismatchError):
            self.create(
                inventory_item=replace(
                    self.item.stock_snapshot(), base_uom=UomCodeVO("G")
                )
            )
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.create(inventory_item=self.item)

    def test_requested_quantity_is_positive_and_multiple_of_step(self) -> None:
        """Нулевой запрос не создаёт обязательство; некратное количество не округляется."""
        for amount in ("0", "-0.000"):
            with self.assertRaises(InvalidStockReservationQuantityError):
                self.create(requested_qty=QuantityVO(Decimal(amount)))
        with self.assertRaises(QuantityStepError):
            self.create(requested_qty=QuantityVO(Decimal("1.23")))
        with self.assertRaises(InvalidStockReservationValueError):
            self.create(requested_qty=Decimal(7))

    def test_partial_and_full_additions_follow_status_and_preserve_identity(
        self,
    ) -> None:
        """Запрос 7 получает удержания 4 и 3 без изменения реквизитов или исходных объектов."""
        pending = self.create()
        partial = self.add(pending)
        full = self.add(partial, "3")
        self.assertEqual(
            (partial.status, partial.reserved_qty.value, partial.version),
            (StockReservationStatus.PARTIALLY_RESERVED, Decimal(4), 1),
        )
        self.assertEqual(
            (full.status, full.reserved_qty.value, full.version),
            (StockReservationStatus.RESERVED, Decimal(7), 2),
        )
        for field in (
            "id",
            "source_ref",
            "pool_id",
            "key",
            "base_uom",
            "requested_qty",
            "created_at",
            "expires_at",
        ):
            self.assertEqual(getattr(full, field), getattr(pending, field))
        self.assertEqual(pending.reserved_qty.value, Decimal(0))

    def test_requested_limit_is_checked_on_every_addition(self) -> None:
        """Превышение собственного запроса отклоняется даже при достаточном общем физическом запасе."""
        pending = self.create()
        with self.assertRaises(StockReservationLimitExceededError):
            self.add(pending, "8")
        partial = self.add(pending)
        with self.assertRaises(StockReservationLimitExceededError):
            self.add(partial, "4")
        full = self.add(partial, "3")
        with self.assertRaises(StockReservationLimitExceededError):
            self.add(full, "0.05")

    def test_release_partial_and_full_and_refill_open_reservation(self) -> None:
        """Частичное освобождение уменьшает текущий резерв; открытое обязательство можно пополнить."""
        full = self.add(self.create(), "7")
        partial = self.release(full)
        self.assertEqual(
            (partial.status, partial.reserved_qty.value),
            (StockReservationStatus.PARTIALLY_RESERVED, Decimal(5)),
        )
        refilled = self.add(partial, "2")
        self.assertEqual(refilled.status, StockReservationStatus.RESERVED)
        closed = self.release(partial, "5")
        self.assertEqual(
            (closed.status, closed.reserved_qty.value, closed.version),
            (StockReservationStatus.RELEASED, Decimal(0), 3),
        )

    def test_release_never_exceeds_own_holding(self) -> None:
        """Нельзя освободить чужую часть общего пула или ненулевое количество из ожидания."""
        with self.assertRaises(StockReservationReleaseExceededError):
            self.release(self.create(), "1")
        partial = self.add(self.create())
        with self.assertRaises(StockReservationReleaseExceededError):
            self.release(partial, "4.05")
        self.assertEqual(partial.reserved_qty.value, Decimal(4))

    def test_add_and_release_reject_zero_raw_and_nonmultiple_quantities(self) -> None:
        """Изменения требуют положительного QuantityVO и точной кратности текущему шагу."""
        partial = self.add(self.create())
        for operation in (self.add, self.release, self.consume):
            for amount in ("0", "-0.000"):
                with self.assertRaises(InvalidStockReservationQuantityError):
                    operation(partial, amount)
            for value in (None, Decimal(1), "1", 1):
                with self.assertRaises(InvalidQuantityError):
                    operation(partial, quantity=value)
            with self.assertRaises(QuantityStepError):
                operation(partial, "0.03")

    def test_release_all_closes_pending_partial_and_full_without_item_context(
        self,
    ) -> None:
        """Закрытие ожидания без удержания допустимо и не требует вызова pool.release(0)."""
        pending = self.create()
        for reservation in (pending, self.add(pending), self.add(pending, "7")):
            closed = self.close(reservation)
            self.assertEqual(
                (closed.status, closed.reserved_qty.value, closed.version),
                (StockReservationStatus.RELEASED, Decimal(0), reservation.version + 1),
            )

    def test_expiration_requires_configured_deadline_and_includes_exact_boundary(
        self,
    ) -> None:
        """До срока завершение запрещено; на границе и позже закрываются любые открытые состояния."""
        with self.assertRaises(StockReservationExpirationError):
            self.expire(self.create(expires_at=None))
        pending = self.create()
        with self.assertRaises(StockReservationExpirationError):
            self.expire(pending, updated_at=self.deadline - timedelta(microseconds=1))
        for reservation in (pending, self.add(pending), self.add(pending, "7")):
            for moment in (self.deadline, self.deadline + timedelta(seconds=1)):
                expired = self.expire(reservation, updated_at=moment)
                self.assertEqual(
                    (expired.status, expired.reserved_qty.value, expired.version),
                    (
                        StockReservationStatus.EXPIRED,
                        Decimal(0),
                        reservation.version + 1,
                    ),
                )

    def test_deadline_blocks_addition_but_release_after_deadline_is_allowed(
        self,
    ) -> None:
        """Срок блокирует только новое удержание; уже принятое можно освободить без ожидания планировщика."""
        pending = self.create()
        before = self.add(
            pending, "1", updated_at=self.deadline - timedelta(microseconds=1)
        )
        self.assertEqual(before.reserved_qty.value, Decimal(1))
        partial = self.add(pending)
        for moment in (self.deadline, self.deadline + timedelta(hours=1)):
            with self.assertRaises(StockReservationExpiredError):
                self.add(partial, "1", updated_at=moment)
            released = self.release(partial, "2", updated_at=moment)
            self.assertEqual(
                (released.status, released.reserved_qty.value),
                (StockReservationStatus.PARTIALLY_RESERVED, Decimal(2)),
            )
            self.assertEqual(
                self.close(partial, updated_at=moment).status,
                StockReservationStatus.RELEASED,
            )

    def test_time_passage_is_not_automatic_expiration(self) -> None:
        """Удержание остаётся в открытом историческом состоянии до явного закрытия и изменения пула."""
        partial = self.add(self.create())
        restored = self.restore(
            reserved_qty=partial.reserved_qty,
            status=partial.status,
            updated_at=self.deadline + timedelta(hours=1),
            version=2,
        )
        self.assertEqual(
            (restored.status, restored.reserved_qty.value),
            (StockReservationStatus.PARTIALLY_RESERVED, Decimal(4)),
        )
        self.assertEqual(self.pool.reserved_qty.value, Decimal(0))

    def test_terminal_states_reject_all_changes_including_repeats(self) -> None:
        """Закрытое обязательство не пополняется, не освобождается и не истекает повторно."""
        for terminal in (self.close(self.create()), self.expire(self.create())):
            for operation in (
                self.add,
                self.release,
                self.close,
                self.expire,
                self.consume,
            ):
                with (
                    self.subTest(status=terminal.status, operation=operation.__name__),
                    self.assertRaises(StockReservationStatusError),
                ):
                    operation(terminal)

    def test_create_and_restore_normalize_aware_times_to_utc(self) -> None:
        """Входные времена с разными смещениями сохраняют один момент и нормализуются в UTC."""
        east = timezone(timedelta(hours=3))
        created = self.create(
            created_at=self.time.astimezone(east),
            expires_at=self.deadline.astimezone(east),
        )
        self.assertEqual(
            (created.created_at, created.updated_at, created.expires_at),
            (self.time, self.time, self.deadline),
        )
        self.assertIs(created.created_at.tzinfo, UTC)
        restored = self.restore(
            created_at=self.time.astimezone(east),
            updated_at=self.time.astimezone(east),
            expires_at=self.deadline.astimezone(east),
        )
        self.assertEqual(restored.created_at, self.time)
        changed = self.add(created, updated_at=self.time.astimezone(east))
        self.assertIs(changed.updated_at.tzinfo, UTC)

    def test_invalid_time_and_chronology_are_domain_errors(self) -> None:
        """Не принимает naive datetime, строки, невозможный UTC-момент и неверную хронологию."""
        for value in (
            None,
            "2026-11-04",
            self.time.replace(tzinfo=None),
            datetime.min.replace(tzinfo=timezone(timedelta(hours=14))),
        ):
            with self.assertRaises(StockReservationTimeError):
                self.create(created_at=value)
        for expires in (
            self.time,
            self.time - timedelta(seconds=1),
            "later",
            self.deadline.replace(tzinfo=None),
        ):
            with self.assertRaises(StockReservationTimeError):
                self.create(expires_at=expires)
        with self.assertRaises(StockReservationTimeError):
            self.restore(updated_at=self.time - timedelta(seconds=1))
        for operation in (
            self.add,
            self.release,
            self.close,
            self.expire,
            self.consume,
        ):
            for value in (
                None,
                "later",
                self.time.replace(tzinfo=None),
                self.time - timedelta(seconds=1),
            ):
                with self.assertRaises(StockReservationTimeError):
                    operation(self.add(self.create()), updated_at=value)

    def test_transition_time_cannot_regress_and_equal_moments_are_allowed(self) -> None:
        """Хронология проверяется по последнему изменению, а не только по моменту создания."""
        partial = self.add(self.create(), updated_at=self.time + timedelta(minutes=1))
        with self.assertRaises(StockReservationTimeError):
            self.add(partial, "1", updated_at=self.time)
        same_time = self.add(partial, "1", updated_at=partial.updated_at)
        self.assertEqual(
            (same_time.updated_at, same_time.version), (partial.updated_at, 2)
        )

    def test_every_transition_requires_strict_expected_version(self) -> None:
        """Ожидаемая версия не принимает bool или сырой числовой тип и должна совпадать с текущей."""
        partial = self.add(self.create())
        for operation in (
            self.add,
            self.release,
            self.close,
            self.expire,
            self.consume,
        ):
            for value in (True, False, -1, None, "1", Decimal(1), 1.0):
                with self.assertRaises(InvalidStockReservationValueError):
                    operation(partial, expected_version=value)
            for value in (0, 2):
                with self.assertRaises(StockReservationVersionConflictError):
                    operation(partial, expected_version=value)

    def test_stale_version_is_checked_before_quantity_arithmetic(self) -> None:
        """Конфликт версии не запускает сложение или вычитание нового удержания."""
        partial = self.add(self.create())
        with patch(
            "src.modules.inventory.domain.policy.quantity_arithmetic.QuantityArithmeticPolicy.add",
            side_effect=RuntimeError("Не складывать"),
        ):
            with self.assertRaises(StockReservationVersionConflictError):
                self.add(partial, expected_version=0)
        with patch(
            "src.modules.inventory.domain.policy.quantity_arithmetic.QuantityArithmeticPolicy.subtract",
            side_effect=RuntimeError("Не вычитать"),
        ):
            with self.assertRaises(StockReservationVersionConflictError):
                self.release(partial, expected_version=0)

    def test_current_item_scope_unit_and_rules_are_rechecked(self) -> None:
        """Увеличение и частичное освобождение требуют того же товара, единицы и текущего шага."""
        partial = self.add(self.create())
        for operation in (self.add, self.release, self.consume):
            with self.assertRaises(InvalidInventoryItemStockSnapshotError):
                operation(partial, inventory_item=self.item.availability_snapshot())
            for changes, error in (
                (
                    dict(inventory_item_id=InventoryItemIdVO(uuid4())),
                    StockReservationItemMismatchError,
                ),
                (dict(base_uom=UomCodeVO("G")), StockReservationUomMismatchError),
                (dict(quantity_rules=QuantityRulesVO(Decimal(2))), QuantityStepError),
            ):
                with self.assertRaises(error):
                    operation(
                        partial,
                        inventory_item=replace(self.item.stock_snapshot(), **changes),
                    )

    def test_restore_preserves_historical_quantities_without_current_rules(
        self,
    ) -> None:
        """Исторический некратный запрос восстанавливается, но не переиспользуется по текущему шагу."""
        historic = self.restore(
            requested_qty=QuantityVO(Decimal("1.23")),
            reserved_qty=QuantityVO(Decimal("0.41")),
            status=StockReservationStatus.PARTIALLY_RESERVED,
            version=8,
        )
        self.assertEqual(
            (
                historic.requested_qty.value,
                historic.reserved_qty.value,
                historic.version,
            ),
            (Decimal("1.23"), Decimal("0.41"), 8),
        )
        for operation in (self.add, self.release, self.consume):
            with self.assertRaises(QuantityStepError):
                operation(historic, "0.05")
        self.assertEqual(self.close(historic).status, StockReservationStatus.RELEASED)
        self.assertEqual(self.expire(historic).status, StockReservationStatus.EXPIRED)

    def test_restore_enforces_status_quantity_matrix(self) -> None:
        """Каждое состояние соответствует собственному удержанию без искусственного обнуления истории."""
        valid = {
            StockReservationStatus.PENDING: {0},
            StockReservationStatus.PARTIALLY_RESERVED: {1, 6},
            StockReservationStatus.RESERVED: {7},
            StockReservationStatus.PARTIALLY_CONSUMED: set(),
            StockReservationStatus.CONSUMED: set(),
            StockReservationStatus.RELEASED: {0},
            StockReservationStatus.EXPIRED: {0},
        }
        for status in StockReservationStatus:
            for amount in (0, 1, 6, 7):
                changes = dict(
                    status=status,
                    reserved_qty=QuantityVO(Decimal(amount)),
                    updated_at=self.deadline,
                )
                with self.subTest(status=status, amount=amount):
                    if amount in valid[status]:
                        self.assertEqual(self.restore(**changes).status, status)
                    else:
                        with self.assertRaises(StockReservationStatusError):
                            self.restore(**changes)
        with self.assertRaises(StockReservationLimitExceededError):
            self.restore(
                reserved_qty=QuantityVO(Decimal(8)),
                status=StockReservationStatus.RESERVED,
            )
        for changes in (dict(expires_at=None), dict(updated_at=self.time)):
            with self.assertRaises(StockReservationExpirationError):
                self.restore(status=StockReservationStatus.EXPIRED, **changes)

    def test_restore_rejects_raw_own_values(self) -> None:
        """Типизированный собственный состав нельзя подменить UUID, строками или bool-версией."""
        for changes in (
            dict(identifier=uuid4()),
            dict(source_ref=None),
            dict(source_ref="ORDER/1"),
            dict(pool_id=uuid4()),
            dict(key={}),
            dict(base_uom="KG"),
            dict(requested_qty=Decimal(7)),
            dict(reserved_qty=None),
            dict(status="PENDING"),
            dict(version=-1),
            dict(version=True),
            dict(version=Decimal(0)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockReservationValueError),
            ):
                self.restore(**changes)
        with self.assertRaises(UnknownUomError):
            self.restore(base_uom=UomCodeVO("BOX"))

    def test_all_tracking_and_expiration_modes_keep_reservation_deadline_independent(
        self,
    ) -> None:
        """Срок обязательства применим и при выключенном учёте дат товара; серии требуют целого шага."""
        for mode in TrackingMode:
            for expiration in ExpirationMode:
                if mode is TrackingMode.NONE and expiration.controls_expiration:
                    continue
                item = InventoryItem.create(
                    identifier=InventoryItemIdVO(uuid4()),
                    sku=SkuVO("MATRIX"),
                    base_uom=UomCodeVO("PCS" if mode.requires_serial else "KG"),
                    quantity_rules=QuantityRulesVO(
                        Decimal(1) if mode.requires_serial else Decimal("0.05")
                    ),
                    tracking_mode=mode,
                    expiration_mode=expiration,
                )
                pool = AvailabilityPool.restore(
                    identifier=AvailabilityPoolIdVO(uuid4()),
                    key=AvailabilityPoolKeyVO(item.id, self.warehouse.id, self.owner),
                    base_uom=item.base_uom,
                    eligible_qty=QuantityVO(Decimal(12)),
                    reserved_qty=QuantityVO(Decimal(0)),
                    assessed_on=self.time.date(),
                    version=0,
                )
                pending = self.create(
                    pool=pool.reservation_snapshot(),
                    inventory_item=item.stock_snapshot(),
                    requested_qty=QuantityVO(Decimal(12)),
                )
                full = self.add(pending, "12", inventory_item=item.stock_snapshot())
                self.assertEqual(
                    (full.status, full.reserved_qty.value),
                    (StockReservationStatus.RESERVED, Decimal(12)),
                )
                self.assertEqual(
                    self.expire(full).status, StockReservationStatus.EXPIRED
                )
                if mode.requires_serial:
                    with self.assertRaises(QuantityStepError):
                        self.release(full, "0.5", inventory_item=item.stock_snapshot())

    def test_many_units_follow_explicit_item_rules(self) -> None:
        """Штучный, весовой, жидкостный, линейный и площадной учёт используют общий контракт количества."""
        for unit in ("PCS", "KG", "L", "M", "M2"):
            item = replace(self.item, base_uom=UomCodeVO(unit))
            pool = replace(self.pool, base_uom=item.base_uom)
            pending = self.create(
                pool=pool.reservation_snapshot(), inventory_item=item.stock_snapshot()
            )
            partial = self.add(pending, "1.25", inventory_item=item.stock_snapshot())
            self.assertEqual(
                (partial.base_uom.value, partial.reserved_qty.value),
                (unit, Decimal("1.25")),
            )

    def test_hostile_decimal_context_does_not_round_or_change_global_flags(
        self,
    ) -> None:
        """Большое удержание точно складывается и освобождается независимо от внешнего Decimal context."""
        pending = self.create(
            requested_qty=QuantityVO(Decimal("12345678901234567890.15"))
        )
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            partial = self.add(pending, "12345678901234567890.10")
            full = self.add(partial, "0.05")
            self.assertEqual(
                (full.status, full.reserved_qty.value),
                (StockReservationStatus.RESERVED, Decimal("12345678901234567890.15")),
            )
            released = self.release(full, "0.05")
            self.assertEqual(released.reserved_qty, partial.reserved_qty)
            self.assertFalse(any(context.flags.values()))

    def test_unrepresentable_counter_arithmetic_is_controlled_error(self) -> None:
        """Защитный предел точной арифметики не заменяется молчаливым округлением удержания."""
        historic = self.restore(
            requested_qty=QuantityVO(Decimal("2E+1000001")),
            reserved_qty=QuantityVO(Decimal("1E+1000001")),
            status=StockReservationStatus.PARTIALLY_RESERVED,
        )
        for operation in (self.add, self.release, self.consume):
            with self.assertRaises(StockQuantityArithmeticError):
                operation(historic, "1")

    def test_pool_and_reservation_transitions_can_be_prepared_consistently(
        self,
    ) -> None:
        """Последовательность 0→4→7→5→0 даёт одинаковые удержания в двух независимых корнях."""
        reservation = self.create()
        pool = self.pool
        for amount in ("4", "3"):
            pool = pool.reserve(
                QuantityVO(Decimal(amount)),
                expected_version=pool.version,
                **self.pool_context(),
            )
            reservation = self.add(reservation, amount)
            self.assertEqual(pool.reserved_qty, reservation.reserved_qty)
        pool = pool.release(
            QuantityVO(Decimal(2)),
            expected_version=pool.version,
            inventory_item=self.item.stock_snapshot(),
        )
        reservation = self.release(reservation)
        self.assertEqual(pool.reserved_qty, reservation.reserved_qty)
        to_release = reservation.reserved_qty
        reservation = self.expire(reservation)
        pool = pool.release(
            to_release,
            expected_version=pool.version,
            inventory_item=self.item.stock_snapshot(),
        )
        self.assertEqual(
            (
                reservation.status,
                reservation.reserved_qty.value,
                pool.reserved_qty.value,
            ),
            (StockReservationStatus.EXPIRED, Decimal(0), Decimal(0)),
        )
        self.assertEqual(
            (self.position.on_hand_qty.value, self.position.version), (Decimal(10), 7)
        )

    def test_snapshot_is_binding_only_and_does_not_authorize_global_capacity(
        self,
    ) -> None:
        """Собственный лимит обязательства не подменяет проверку свободного количества общим пулом."""
        empty_pool = replace(self.pool, eligible_qty=QuantityVO(Decimal(0)))
        reservation = self.create(pool=empty_pool.reservation_snapshot())
        candidate = self.add(reservation)
        self.assertEqual(candidate.reserved_qty.value, Decimal(4))
        with self.assertRaises(InsufficientAvailableStockError):
            empty_pool.reserve(
                QuantityVO(Decimal(4)),
                expected_version=0,
                **(self.pool_context() | dict(positions=(), locations=())),
            )
        self.assertEqual(
            (empty_pool.reserved_qty.value, reservation.reserved_qty.value),
            (Decimal(0), Decimal(0)),
        )

    def test_failure_of_one_candidate_does_not_persist_other_candidate(self) -> None:
        """Подготовленный кандидат пула не является сохранением, если лимит обязательства отклоняет шаг."""
        reservation = self.create(requested_qty=QuantityVO(Decimal(3)))
        candidate = self.pool.reserve(
            QuantityVO(Decimal(7)), expected_version=0, **self.pool_context()
        )
        with self.assertRaises(StockReservationLimitExceededError):
            self.add(reservation, "7")
        self.assertEqual(candidate.reserved_qty.value, Decimal(7))
        self.assertEqual(
            (self.pool.reserved_qty.value, reservation.reserved_qty.value),
            (Decimal(0), Decimal(0)),
        )

    def test_version_is_not_database_lock_or_command_idempotency(self) -> None:
        """Две ветви старого состояния и повтор с актуальной версией требуют внешнего контроля записи."""
        pending = self.create()
        first = self.add(pending, "2")
        second = self.add(pending, "2")
        self.assertEqual(first.reserved_qty, second.reserved_qty)
        with self.assertRaises(StockReservationVersionConflictError):
            self.add(first, "2", expected_version=0)
        repeated = self.add(first, "2")
        self.assertEqual(repeated.reserved_qty.value, Decimal(4))

    def test_direct_invalid_state_cannot_bypass_public_methods(self) -> None:
        """Публичные методы повторно валидируют прямой dataclass-конструктор и UTC-хранение."""
        reservation = self.create()
        for changes, error in (
            (dict(version=True), InvalidStockReservationValueError),
            (dict(source_ref=None), InvalidStockReservationValueError),
            (dict(reserved_qty=QuantityVO(Decimal(1))), StockReservationStatusError),
            (
                dict(requested_qty=QuantityVO(Decimal(0))),
                InvalidStockReservationQuantityError,
            ),
            (
                dict(created_at=self.time.astimezone(timezone(timedelta(hours=2)))),
                StockReservationTimeError,
            ),
        ):
            malformed = replace(reservation, **changes)
            for operation in (
                self.add,
                self.release,
                self.close,
                self.expire,
                self.consume,
            ):
                with self.assertRaises(error):
                    operation(malformed)

    def test_success_and_failure_leave_originals_immutable(self) -> None:
        """Новые версии не изменяют исходное обязательство, общий пул или физические позиции."""
        pending = self.create()
        before = (
            self.pool.reserved_qty,
            self.pool.version,
            self.position.on_hand_qty,
            self.position.version,
        )
        partial = self.add(pending)
        with self.assertRaises(StockReservationLimitExceededError):
            self.add(partial, "4")
        self.assertEqual((pending.reserved_qty.value, pending.version), (Decimal(0), 0))
        self.assertEqual((partial.reserved_qty.value, partial.version), (Decimal(4), 1))
        self.assertEqual(
            (
                self.pool.reserved_qty,
                self.pool.version,
                self.position.on_hand_qty,
                self.position.version,
            ),
            before,
        )
        with self.assertRaises(FrozenInstanceError):
            partial.reserved_qty = QuantityVO(Decimal(0))

    def test_consumption_moves_hold_into_history_and_completes_exact_request(
        self,
    ) -> None:
        """Запрос 7 после погашений 4 и 3 сохраняет историю и становится CONSUMED."""
        full = self.add(self.create(), "7")
        partial = self.consume(full, "4")
        consumed = self.consume(partial, "3")
        self.assertEqual(
            (
                partial.reserved_qty.value,
                partial.consumed_qty.value,
                partial.status,
                partial.version,
            ),
            (Decimal(3), Decimal(4), StockReservationStatus.PARTIALLY_CONSUMED, 2),
        )
        self.assertEqual(
            (
                consumed.reserved_qty.value,
                consumed.consumed_qty.value,
                consumed.status,
                consumed.version,
            ),
            (Decimal(0), Decimal(7), StockReservationStatus.CONSUMED, 3),
        )
        for field in (
            "id",
            "key",
            "pool_id",
            "base_uom",
            "source_ref",
            "requested_qty",
            "expires_at",
            "created_at",
        ):
            self.assertEqual(getattr(consumed, field), getattr(full, field))
        self.assertEqual(
            (full.reserved_qty.value, full.consumed_qty.value), (Decimal(7), Decimal(0))
        )
        self.assertEqual(self.pool.reserved_qty.value, Decimal(0))
        with self.assertRaises(FrozenInstanceError):
            consumed.consumed_qty = QuantityVO(Decimal(0))

    def test_consumption_never_exceeds_current_own_holding(self) -> None:
        """Погашение требует уже удерживаемое количество и не может занять чужой резерв пула."""
        for reservation, quantity in (
            (self.create(), "1"),
            (self.add(self.create()), "4.05"),
        ):
            with self.assertRaises(StockReservationConsumptionExceededError):
                self.consume(reservation, quantity)

    def test_consumed_part_cannot_be_reserved_twice_after_partial_release(self) -> None:
        """При запросе 7, погашении 4 и удержании 2 допустимо зарезервировать только ещё 1."""
        partial = self.consume(self.add(self.create(), "7"))
        released = self.release(partial, "1")
        self.assertEqual(
            (released.status, released.reserved_qty.value, released.consumed_qty.value),
            (StockReservationStatus.PARTIALLY_CONSUMED, Decimal(2), Decimal(4)),
        )
        with self.assertRaises(StockReservationLimitExceededError):
            self.add(released, "1.05")
        refilled = self.add(released, "1")
        self.assertEqual(
            (refilled.reserved_qty.value, refilled.consumed_qty.value, refilled.status),
            (Decimal(3), Decimal(4), StockReservationStatus.PARTIALLY_CONSUMED),
        )

    def test_partial_consumption_with_no_hold_remains_open_for_unfulfilled_part(
        self,
    ) -> None:
        """Использование всего частичного удержания не закрывает неисполненную часть запроса."""
        partial = self.consume(self.add(self.create(), "4"), "4")
        self.assertEqual(
            (
                partial.reserved_qty.value,
                partial.consumed_qty.value,
                partial.status.is_terminal,
            ),
            (Decimal(0), Decimal(4), False),
        )
        replenished = self.add(partial, "3")
        self.assertEqual(
            self.consume(replenished, "3").status, StockReservationStatus.CONSUMED
        )
        for closed in (self.close(partial), self.expire(partial)):
            self.assertEqual(
                (closed.reserved_qty.value, closed.consumed_qty.value),
                (Decimal(0), Decimal(4)),
            )

    def test_release_close_and_expire_preserve_consumed_history(self) -> None:
        """Все способы прекращения удержания сохраняют уже использованные 4 единицы."""
        partial = self.consume(self.add(self.create(), "7"), "4")
        for closed in (
            self.release(partial, "3"),
            self.close(partial),
            self.expire(partial),
        ):
            self.assertEqual(
                (closed.reserved_qty.value, closed.consumed_qty.value),
                (Decimal(0), Decimal(4)),
            )
            self.assertTrue(closed.status.is_terminal)
        self.assertEqual(partial.consumed_qty.value, Decimal(4))

    def test_consumed_is_terminal_for_all_transitions(self) -> None:
        """Полностью исполненное обязательство нельзя закрыть, освободить или использовать повторно."""
        consumed = self.consume(self.add(self.create(), "7"), "7")
        for operation in (
            self.add,
            self.release,
            self.close,
            self.expire,
            self.consume,
        ):
            with self.assertRaises(StockReservationStatusError):
                operation(consumed)

    def test_consumption_deadline_is_checked_by_fact_time_and_registration_can_be_late(
        self,
    ) -> None:
        """Факт до срока можно зарегистрировать позже, но закрытое обязательство не восстанавливается."""
        reserved = self.add(self.create(), "7")
        for moment in (self.deadline, self.deadline + timedelta(microseconds=1)):
            with self.assertRaises(StockReservationExpiredError):
                self.consume(reserved, consumed_at=moment, updated_at=moment)
        late = self.consume(
            reserved,
            consumed_at=self.deadline - timedelta(microseconds=1),
            updated_at=self.deadline + timedelta(hours=1),
        )
        self.assertEqual(
            (late.consumed_qty.value, late.status),
            (Decimal(4), StockReservationStatus.PARTIALLY_CONSUMED),
        )
        with self.assertRaises(StockReservationStatusError):
            self.consume(
                self.expire(reserved), consumed_at=self.time, updated_at=self.deadline
            )
        no_deadline = self.add(self.create(expires_at=None), "7")
        self.assertEqual(
            self.consume(
                no_deadline, "7", consumed_at=self.deadline, updated_at=self.deadline
            ).status,
            StockReservationStatus.CONSUMED,
        )

    def test_consumption_time_requires_aware_valid_fact_and_monotonic_registration(
        self,
    ) -> None:
        """Факт ограничен созданием и регистрацией, а время регистрации не может идти назад."""
        reserved = self.add(self.create(), "7")
        for value in (
            None,
            "now",
            self.time.replace(tzinfo=None),
            self.time - timedelta(microseconds=1),
            self.time + timedelta(microseconds=1),
        ):
            with self.assertRaises(StockReservationTimeError):
                self.consume(reserved, consumed_at=value)
        west = timezone(timedelta(hours=-5))
        registered = self.consume(
            reserved,
            consumed_at=self.time.astimezone(west),
            updated_at=self.time.astimezone(west),
        )
        self.assertIs(registered.updated_at.tzinfo, UTC)
        later = self.consume(reserved, "1", updated_at=self.time + timedelta(minutes=5))
        with self.assertRaises(StockReservationTimeError):
            self.consume(later, "1", updated_at=self.time)

    def test_consumed_history_restore_is_explicit_and_checks_three_quantity_status_matrix(
        self,
    ) -> None:
        """Матрица отличает историю использования от оставшегося удержания во всех статусах."""
        cases = (
            (StockReservationStatus.PARTIALLY_CONSUMED, 0, 4, True),
            (StockReservationStatus.PARTIALLY_CONSUMED, 1, 4, True),
            (StockReservationStatus.PARTIALLY_CONSUMED, 3, 4, True),
            (StockReservationStatus.CONSUMED, 0, 7, True),
            (StockReservationStatus.RELEASED, 0, 4, True),
            (StockReservationStatus.EXPIRED, 0, 4, True),
            (StockReservationStatus.PENDING, 0, 1, False),
            (StockReservationStatus.PARTIALLY_RESERVED, 1, 1, False),
            (StockReservationStatus.RESERVED, 3, 4, False),
            (StockReservationStatus.PARTIALLY_CONSUMED, 0, 0, False),
            (StockReservationStatus.PARTIALLY_CONSUMED, 0, 7, False),
            (StockReservationStatus.CONSUMED, 0, 6, False),
            (StockReservationStatus.RELEASED, 0, 7, False),
            (StockReservationStatus.EXPIRED, 0, 7, False),
        )
        for status, held, used, valid in cases:
            changes = dict(
                status=status,
                reserved_qty=QuantityVO(Decimal(held)),
                consumed_qty=QuantityVO(Decimal(used)),
                updated_at=self.deadline,
            )
            with self.subTest(status=status, held=held, used=used):
                if valid:
                    restored = self.restore(**changes)
                    self.assertEqual(restored.consumed_qty.value, Decimal(used))
                else:
                    with self.assertRaises(StockReservationStatusError):
                        self.restore(**changes)
        for held, used in ((1, 7), (0, 8), (4, 4)):
            with self.assertRaises(StockReservationLimitExceededError):
                self.restore(
                    reserved_qty=QuantityVO(Decimal(held)),
                    consumed_qty=QuantityVO(Decimal(used)),
                    status=StockReservationStatus.PARTIALLY_CONSUMED,
                )
        with self.assertRaises(InvalidStockReservationValueError):
            self.restore(consumed_qty=Decimal(1))
        with self.assertRaises(TypeError):
            StockReservation.restore(
                identifier=StockReservationIdVO(uuid4()),
                source_ref=self.source,
                pool_id=self.pool.id,
                key=self.key,
                base_uom=self.item.base_uom,
                requested_qty=QuantityVO(Decimal(7)),
                reserved_qty=QuantityVO(Decimal(0)),
                status=StockReservationStatus.PENDING,
                expires_at=self.deadline,
                created_at=self.time,
                updated_at=self.time,
                version=0,
            )

    def test_consumption_current_step_checks_consumed_counter_without_rewriting_history(
        self,
    ) -> None:
        """Восстановленная история сохраняется; текущий шаг проверяется при новом изменении количества."""
        historic = self.restore(
            requested_qty=QuantityVO(Decimal(7)),
            reserved_qty=QuantityVO(Decimal(2)),
            consumed_qty=QuantityVO(Decimal("0.01")),
            status=StockReservationStatus.PARTIALLY_CONSUMED,
        )
        for operation in (self.add, self.release, self.consume):
            with self.assertRaises(QuantityStepError):
                operation(historic, "0.05")
        self.assertEqual(self.close(historic).consumed_qty.value, Decimal("0.01"))
        self.assertEqual(self.expire(historic).consumed_qty.value, Decimal("0.01"))

    def test_consumption_hostile_decimal_context_is_exact(self) -> None:
        """Новый тройной инвариант и перенос между счётчиками не используют внешнюю точность."""
        requested = QuantityVO(Decimal("12345678901234567890.15"))
        reserved = self.add(self.create(requested_qty=requested), str(requested.value))
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            partial = self.consume(reserved, "12345678901234567890.10")
            self.assertEqual(
                (partial.reserved_qty.value, partial.consumed_qty.value),
                (Decimal("0.05"), Decimal("12345678901234567890.10")),
            )
            full = self.consume(partial, "0.05")
            self.assertEqual(
                (full.status, full.consumed_qty),
                (StockReservationStatus.CONSUMED, requested),
            )
            self.assertFalse(any(context.flags.values()))

    def test_consumption_unrepresentable_arithmetic_is_controlled(self) -> None:
        """Погашение не округляет результат при превышении защитного предела точной арифметики."""
        reserved = self.restore(
            requested_qty=QuantityVO(Decimal("1E+1000001")),
            reserved_qty=QuantityVO(Decimal("1E+1000001")),
            status=StockReservationStatus.RESERVED,
        )
        with self.assertRaises(StockQuantityArithmeticError):
            self.consume(reserved, "1")

    def test_consumption_supports_serial_whole_counts_without_instance_selection(
        self,
    ) -> None:
        """Мягкое погашение серийных товаров допускает много целых PCS и запрещает дробь."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = InventoryItem.create(
                identifier=InventoryItemIdVO(uuid4()),
                sku=SkuVO("SERIAL"),
                base_uom=UomCodeVO("PCS"),
                quantity_rules=QuantityRulesVO(Decimal(1)),
                tracking_mode=mode,
            )
            pool = replace(
                self.pool,
                key=AvailabilityPoolKeyVO(item.id, self.warehouse.id, self.owner),
                base_uom=item.base_uom,
            )
            pending = self.create(
                pool=pool.reservation_snapshot(), inventory_item=item.stock_snapshot()
            )
            reserved = self.add(pending, "7", inventory_item=item.stock_snapshot())
            with self.assertRaises(QuantityStepError):
                self.consume(reserved, "0.5", inventory_item=item.stock_snapshot())
            partial = self.consume(reserved, "4", inventory_item=item.stock_snapshot())
            self.assertEqual(
                (partial.consumed_qty.value, partial.reserved_qty.value),
                (Decimal(4), Decimal(3)),
            )

    def test_consumption_and_post_issue_pool_keep_available_stock_without_double_subtraction(
        self,
    ) -> None:
        """После расхода 4 из 10 и погашения резерва 7 пул содержит 6/3 со свободными 3."""
        reserved = self.add(self.create(), "7")
        pool = self.pool.reserve(
            QuantityVO(Decimal(7)), expected_version=0, **self.pool_context()
        )
        after_issue = self.position.apply_delta(
            StockDeltaVO(Decimal(-4)),
            inventory_item=self.item.stock_snapshot(),
            location=self.location,
            warehouse=self.warehouse,
        )
        partial = self.consume(reserved, "4")
        pool_after = pool.consume_reserved(
            QuantityVO(Decimal(4)),
            expected_version=pool.version,
            **(
                self.pool_context()
                | dict(positions=(after_issue.availability_snapshot(),))
            ),
        )
        self.assertEqual(
            (
                pool_after.eligible_qty.value,
                pool_after.reserved_qty.value,
                pool_after.available_qty.value,
                pool_after.version,
            ),
            (Decimal(6), Decimal(3), Decimal(3), 2),
        )
        self.assertEqual(partial.reserved_qty, pool_after.reserved_qty)
        after_second_issue = after_issue.apply_delta(
            StockDeltaVO(Decimal(-3)),
            inventory_item=self.item.stock_snapshot(),
            location=self.location,
            warehouse=self.warehouse,
        )
        completed = self.consume(partial, "3")
        completed_pool = pool_after.consume_reserved(
            QuantityVO(Decimal(3)),
            expected_version=pool_after.version,
            **(
                self.pool_context()
                | dict(positions=(after_second_issue.availability_snapshot(),))
            ),
        )
        self.assertEqual(
            (
                completed.status,
                completed.consumed_qty.value,
                completed_pool.eligible_qty.value,
                completed_pool.reserved_qty.value,
                completed_pool.available_qty.value,
            ),
            (
                StockReservationStatus.CONSUMED,
                Decimal(7),
                Decimal(3),
                Decimal(0),
                Decimal(3),
            ),
        )
        self.assertEqual(
            (
                self.position.on_hand_qty.value,
                self.position.version,
                self.pool.reserved_qty.value,
            ),
            (Decimal(10), 7, Decimal(0)),
        )

    def test_consumption_candidate_failure_is_not_partial_persistence(self) -> None:
        """Корректный кандидат обязательства не является сохранением при ошибке общего пула."""
        reserved = self.add(self.create(), "7")
        candidate = self.consume(reserved, "4")
        empty_pool = self.pool
        from src.modules.inventory.domain.availability_pool.error import (
            ExcessiveReservationConsumptionError,
        )

        with self.assertRaises(ExcessiveReservationConsumptionError):
            empty_pool.consume_reserved(
                QuantityVO(Decimal(4)), expected_version=0, **self.pool_context()
            )
        self.assertEqual(candidate.consumed_qty.value, Decimal(4))
        self.assertEqual(
            (
                reserved.consumed_qty.value,
                reserved.reserved_qty.value,
                empty_pool.reserved_qty.value,
            ),
            (Decimal(0), Decimal(7), Decimal(0)),
        )


if __name__ == "__main__":
    unittest.main()
