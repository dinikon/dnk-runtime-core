from datetime import date
from decimal import Decimal

from src.modules.inventory.domain.error import (
    DuplicatePositiveSerialStockError,
    ExpirationDateRequiredError,
    InvalidStockAvailabilityContextError,
)
from src.modules.inventory.domain.inventory_item.availability_snapshot import (
    InventoryItemAvailabilitySnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemAvailabilitySnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.policy.stock_dimensions import StockDimensionsPolicy
from src.modules.inventory.domain.policy.stock_expiration import StockExpirationPolicy
from src.modules.inventory.domain.policy.stock_serial import StockSerialPolicy
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
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.availability_snapshot import (
    StockPositionAvailabilitySnapshot,
)
from src.modules.inventory.domain.stock_position.error import (
    InvalidStockPositionAvailabilitySnapshotError,
    StockPositionUomMismatchError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_serial.availability_snapshot import (
    StockSerialAvailabilitySnapshot,
)
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class StockAvailabilityPolicy:
    """Рассчитывает пригодный к резервированию физический запас без вычета действующих резервов."""

    @staticmethod
    def calculate_eligible_quantity(
        *,
        inventory_item: InventoryItemAvailabilitySnapshot,
        warehouse: WarehouseSnapshot,
        owner_id: StockOwnerIdVO,
        as_of: date,
        positions: tuple[StockPositionAvailabilitySnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialAvailabilitySnapshot, ...] = (),
    ) -> QuantityVO:
        """Суммирует SELLABLE в активных STORAGE по явной календарной дате и одной области учёта."""
        if not isinstance(inventory_item, InventoryItemAvailabilitySnapshot):
            raise InvalidInventoryItemAvailabilitySnapshotError(
                "Нужен снимок правил доступности товара."
            )
        inventory_item.ensure_valid()
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок склада расчёта.")
        warehouse.ensure_valid()
        if not isinstance(owner_id, StockOwnerIdVO) or type(as_of) is not date:
            raise InvalidStockAvailabilityContextError(
                "Нужны типизированный владелец и явная календарная date без времени."
            )
        if not all(
            isinstance(values, tuple)
            for values in (positions, locations, lots, serials)
        ):
            raise InvalidStockAvailabilityContextError(
                "Контекст доступности передаётся в tuple снимков."
            )

        by_location: dict[StockLocationIdVO, StockLocationSnapshot] = {}
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidStockLocationSnapshotError("Нужны снимки локаций расчёта.")
            location.ensure_valid()
            if location.id in by_location:
                raise InvalidStockAvailabilityContextError("Повтор снимка локации.")
            by_location[location.id] = location
        by_lot: dict[StockLotIdVO, StockLotSnapshot] = {}
        for lot in lots:
            if (
                not isinstance(lot, StockLotSnapshot)
                or not isinstance(lot.id, StockLotIdVO)
                or not isinstance(lot.inventory_item_id, InventoryItemIdVO)
                or not isinstance(lot.dates, StockDatesVO)
            ):
                raise InvalidStockLotSnapshotError(
                    "Нужны типизированные снимки партий с датами."
                )
            if lot.id in by_lot:
                raise InvalidStockAvailabilityContextError("Повтор снимка партии.")
            by_lot[lot.id] = lot
        by_serial: dict[StockSerialIdVO, StockSerialAvailabilitySnapshot] = {}
        for serial in serials:
            if not isinstance(serial, StockSerialAvailabilitySnapshot):
                raise InvalidStockSerialSnapshotError(
                    "Нужны снимки экземпляров для доступности."
                )
            serial.ensure_valid()
            if serial.id in by_serial:
                raise InvalidStockAvailabilityContextError("Повтор снимка экземпляра.")
            by_serial[serial.id] = serial

        used_locations: set[StockLocationIdVO] = set()
        used_lots: set[StockLotIdVO] = set()
        used_serials: set[StockSerialIdVO] = set()
        position_ids: set[StockPositionIdVO] = set()
        dimensions_seen: set[StockDimensionsVO] = set()
        positive_serials: set[StockSerialIdVO] = set()
        eligible: list[StockPositionAvailabilitySnapshot] = []
        stock_item = inventory_item.stock_snapshot()
        tracking_item = inventory_item.tracking_snapshot()
        for position in positions:
            if not isinstance(position, StockPositionAvailabilitySnapshot):
                raise InvalidStockPositionAvailabilitySnapshotError(
                    "Нужны снимки физического количества позиций."
                )
            position.ensure_valid()
            dimensions = position.dimensions
            if position.id in position_ids or dimensions in dimensions_seen:
                raise InvalidStockAvailabilityContextError(
                    "Повтор ID позиции или полного ключа измерений."
                )
            position_ids.add(position.id)
            dimensions_seen.add(dimensions)
            if dimensions.owner_id != owner_id:
                raise InvalidStockAvailabilityContextError(
                    "Позиция принадлежит другому владельцу."
                )
            location = by_location.get(dimensions.location_id)
            if location is None:
                raise InvalidStockAvailabilityContextError(
                    "Отсутствует снимок локации позиции."
                )
            used_locations.add(location.id)
            lot = by_lot.get(dimensions.lot_id)
            serial = by_serial.get(dimensions.serial_id)
            if dimensions.lot_id is not None:
                used_lots.add(dimensions.lot_id)
            if dimensions.serial_id is not None:
                used_serials.add(dimensions.serial_id)
            StockDimensionsPolicy.ensure_compatible(
                dimensions=dimensions,
                inventory_item=stock_item,
                location=location,
                warehouse=warehouse,
                lot=lot,
                serial=serial.identity_snapshot() if serial is not None else None,
            )
            if position.base_uom != inventory_item.base_uom:
                raise StockPositionUomMismatchError(
                    "Единица позиции не совпадает с базовой единицей товара."
                )
            QuantityValidationPolicy.validate(
                quantity=position.on_hand_qty, rules=inventory_item.quantity_rules
            )
            if (
                dimensions.serial_id is not None
                and not position.on_hand_qty.value.is_zero()
            ):
                if dimensions.serial_id in positive_serials:
                    raise DuplicatePositiveSerialStockError(
                        "Один экземпляр имеет положительный остаток в нескольких позициях набора."
                    )
                positive_serials.add(dimensions.serial_id)

            dates = None
            if serial is not None:
                dates = StockSerialPolicy.resolve_dates(
                    inventory_item_id=serial.inventory_item_id,
                    inventory_item=tracking_item,
                    lot_id=serial.lot_id,
                    dates=serial.dates,
                    lot=lot,
                )
            elif inventory_item.tracking_mode is TrackingMode.LOT:
                dates = lot.dates
            unexpired = StockAvailabilityPolicy._is_unexpired(
                dates=dates,
                expiration_mode=inventory_item.expiration_mode,
                quantity=position.on_hand_qty,
                as_of=as_of,
            )
            if (
                warehouse.is_active
                and location.is_active
                and location.location_type is LocationType.STORAGE
                and dimensions.stock_status is StockStatus.SELLABLE
                and unexpired
            ):
                eligible.append(position)

        if (
            used_locations != set(by_location)
            or used_lots != set(by_lot)
            or used_serials != set(by_serial)
        ):
            raise InvalidStockAvailabilityContextError(
                "Нужны ровно участвующие снимки локаций, партий и экземпляров."
            )
        result = QuantityVO(Decimal(0))
        for position in sorted(eligible, key=lambda value: value.id.value.int):
            result = QuantityArithmeticPolicy.add(result, position.on_hand_qty)
        QuantityValidationPolicy.validate(
            quantity=result, rules=inventory_item.quantity_rules
        )
        return result

    @staticmethod
    def _is_unexpired(
        *,
        dates: StockDatesVO | None,
        expiration_mode: ExpirationMode,
        quantity: QuantityVO,
        as_of: date,
    ) -> bool:
        """Считает последний день допустимым; обязательный срок требуется лишь положительному остатку."""
        if dates is not None:
            StockExpirationPolicy.ensure_dates_allowed(
                dates=dates, expiration_mode=expiration_mode
            )
        if not expiration_mode.controls_expiration:
            return True
        if dates is None or dates.expires_on is None:
            if not quantity.value.is_zero():
                raise ExpirationDateRequiredError(
                    "Для расчёта доступности положительного остатка REQUIRED нужен срок годности."
                )
            return True
        return dates.expires_on >= as_of
