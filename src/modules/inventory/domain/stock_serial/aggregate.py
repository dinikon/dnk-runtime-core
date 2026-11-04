from dataclasses import dataclass, replace
from typing import Self

from src.modules.inventory.domain.stock_serial.availability_snapshot import (
    StockSerialAvailabilitySnapshot,
)
from src.modules.inventory.domain.stock_serial.execution_snapshot import (
    StockSerialExecutionSnapshot,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemTrackingSnapshotError,
)
from src.modules.inventory.domain.inventory_item.snapshot import (
    InventoryItemTrackingSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_expiration import StockExpirationPolicy
from src.modules.inventory.domain.policy.stock_serial import StockSerialPolicy
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.error import (
    InvalidSerialConfigurationError,
    InvalidStockSerialValueError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


@dataclass(frozen=True, slots=True)
class StockSerial:
    """Идентичность одного экземпляра с собственными датами либо ссылкой на партию."""

    id: StockSerialIdVO
    inventory_item_id: InventoryItemIdVO
    number: SerialNumberVO
    lot_id: StockLotIdVO | None
    dates: StockDatesVO | None

    @classmethod
    def create(
        cls,
        *,
        identifier: StockSerialIdVO,
        inventory_item: InventoryItemTrackingSnapshot,
        number: SerialNumberVO,
        dates: StockDatesVO | None,
        lot: StockLotSnapshot | None = None,
    ) -> Self:
        """Создаёт экземпляр по снимкам, допуская неполный срок до поступления."""
        if not isinstance(inventory_item, InventoryItemTrackingSnapshot):
            raise InvalidInventoryItemTrackingSnapshotError(
                "Для создания экземпляра нужен снимок прослеживаемости товара."
            )
        if lot is not None and not isinstance(lot, StockLotSnapshot):
            raise InvalidStockLotSnapshotError(
                "Ожидался снимок партии StockLotSnapshot."
            )
        serial = cls.restore(
            identifier=identifier,
            inventory_item_id=inventory_item.inventory_item_id,
            number=number,
            lot_id=lot.id if lot is not None else None,
            dates=dates,
        )
        serial._validated_dates(inventory_item=inventory_item, lot=lot)
        return serial

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockSerialIdVO,
        inventory_item_id: InventoryItemIdVO,
        number: SerialNumberVO,
        lot_id: StockLotIdVO | None,
        dates: StockDatesVO | None,
    ) -> Self:
        """Восстанавливает собственную идентичность и источник дат без текущих снимков."""
        serial = cls(identifier, inventory_item_id, number, lot_id, dates)
        serial._validate()
        return serial

    def availability_snapshot(self) -> StockSerialAvailabilitySnapshot:
        """Возвращает проверенные идентичность и источник дат для расчёта доступности."""
        self._validate()
        return StockSerialAvailabilitySnapshot(
            self.id, self.inventory_item_id, self.lot_id, self.dates
        )

    def execution_snapshot(self) -> StockSerialExecutionSnapshot:
        """Возвращает проверенные идентичность и источник дат для фактического исполнения."""
        self._validate()
        return StockSerialExecutionSnapshot(
            self.id, self.inventory_item_id, self.lot_id, self.dates
        )

    def snapshot(self) -> StockSerialSnapshot:
        """Возвращает проверенную идентичность и связь с партией без передачи корня."""
        self._validate()
        return StockSerialSnapshot(self.id, self.inventory_item_id, self.lot_id)

    def change_dates(
        self, dates: StockDatesVO, *, inventory_item: InventoryItemTrackingSnapshot
    ) -> Self:
        """Возвращает самостоятельный экземпляр с новыми датами и прежней идентичностью."""
        self._validate()
        if self.lot_id is not None:
            raise InvalidSerialConfigurationError(
                "Даты экземпляра партии изменяются через StockLot."
            )
        candidate = replace(self, dates=dates)
        candidate._validate()
        candidate._validated_dates(inventory_item=inventory_item, lot=None)
        return candidate

    def ensure_ready_for_receipt(
        self,
        *,
        inventory_item: InventoryItemTrackingSnapshot,
        lot: StockLotSnapshot | None = None,
    ) -> None:
        """Проверяет текущие снимки и полноту срока из единственного источника дат."""
        self._validate()
        dates = self._validated_dates(inventory_item=inventory_item, lot=lot)
        StockExpirationPolicy.ensure_ready_for_receipt(
            dates=dates, expiration_mode=inventory_item.expiration_mode
        )

    def _validated_dates(
        self,
        *,
        inventory_item: InventoryItemTrackingSnapshot,
        lot: StockLotSnapshot | None,
    ) -> StockDatesVO:
        """Выбирает даты по межагрегатным правилам и проверяет допустимость их заполнения."""
        dates = StockSerialPolicy.resolve_dates(
            inventory_item_id=self.inventory_item_id,
            inventory_item=inventory_item,
            lot_id=self.lot_id,
            dates=self.dates,
            lot=lot,
        )
        StockExpirationPolicy.ensure_dates_allowed(
            dates=dates, expiration_mode=inventory_item.expiration_mode
        )
        return dates

    def _validate(self) -> None:
        """Проверяет собственные типы и наличие ровно одного источника дат."""
        if (
            not isinstance(self.id, StockSerialIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.number, SerialNumberVO)
            or (self.lot_id is not None and not isinstance(self.lot_id, StockLotIdVO))
            or (self.dates is not None and not isinstance(self.dates, StockDatesVO))
        ):
            raise InvalidStockSerialValueError(
                "Нужны типизированные ID, серийный номер и источник дат экземпляра."
            )
        if (self.lot_id is None and self.dates is None) or (
            self.lot_id is not None and self.dates is not None
        ):
            raise InvalidSerialConfigurationError(
                "Нужны либо собственные даты, либо ссылка на партию."
            )
