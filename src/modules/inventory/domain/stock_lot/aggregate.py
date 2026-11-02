from dataclasses import dataclass, replace
from typing import Self

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
from src.modules.inventory.domain.policy.stock_lot import StockLotPolicy
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotValueError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_dates import LotDatesVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO


@dataclass(frozen=True, slots=True)
class StockLot:
    """Самостоятельная партия товара без количества, складов и дочерних Entity."""

    id: StockLotIdVO
    inventory_item_id: InventoryItemIdVO
    number: LotNumberVO
    dates: LotDatesVO

    @classmethod
    def create(
        cls,
        *,
        identifier: StockLotIdVO,
        inventory_item: InventoryItemTrackingSnapshot,
        number: LotNumberVO,
        dates: LotDatesVO,
    ) -> Self:
        """Создаёт партию по снимку товара, допуская неполные даты для REQUIRED."""
        if not isinstance(inventory_item, InventoryItemTrackingSnapshot):
            raise InvalidInventoryItemTrackingSnapshotError(
                "Для создания партии нужен снимок прослеживаемости товара."
            )
        lot = cls.restore(
            identifier=identifier,
            inventory_item_id=inventory_item.inventory_item_id,
            number=number,
            dates=dates,
        )
        lot._ensure_compatible(inventory_item)
        return lot

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockLotIdVO,
        inventory_item_id: InventoryItemIdVO,
        number: LotNumberVO,
        dates: LotDatesVO,
    ) -> Self:
        """Восстанавливает собственное состояние без текущих настроек другого агрегата."""
        lot = cls(identifier, inventory_item_id, number, dates)
        lot._validate()
        return lot

    def change_dates(
        self, dates: LotDatesVO, *, inventory_item: InventoryItemTrackingSnapshot
    ) -> Self:
        """Возвращает партию с новыми датами, проверяя принадлежность и настройки товара."""
        candidate = replace(self, dates=dates)
        candidate._validate()
        candidate._ensure_compatible(inventory_item)
        return candidate

    def ensure_ready_for_receipt(
        self, *, inventory_item: InventoryItemTrackingSnapshot
    ) -> None:
        """Проверяет текущую совместимость и полноту срока перед будущим поступлением."""
        self._validate()
        self._ensure_compatible(inventory_item)
        StockExpirationPolicy.ensure_ready_for_receipt(
            dates=self.dates, expiration_mode=inventory_item.expiration_mode
        )

    def _ensure_compatible(self, inventory_item: InventoryItemTrackingSnapshot) -> None:
        """Проверяет межагрегатные правила по явно переданному снимку без I/O."""
        StockLotPolicy.ensure_compatible(
            inventory_item_id=self.inventory_item_id, inventory_item=inventory_item
        )
        StockExpirationPolicy.ensure_dates_allowed(
            dates=self.dates, expiration_mode=inventory_item.expiration_mode
        )

    def _validate(self) -> None:
        """Проверяет типы собственных значений и неизменяемую идентичность партии."""
        if (
            not isinstance(self.id, StockLotIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.number, LotNumberVO)
            or not isinstance(self.dates, LotDatesVO)
        ):
            raise InvalidStockLotValueError(
                "Нужны типизированные ID, номер и даты партии."
            )
