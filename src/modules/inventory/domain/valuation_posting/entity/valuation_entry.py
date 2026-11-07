from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_posting.error import (
    InvalidValuationEntryError,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_id import (
    ValuationEntryIdVO,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class ValuationEntry:
    """Фиксирует стоимость одной записи прихода внутри агрегата ValuationPosting."""

    id: ValuationEntryIdVO
    ledger_entry_id: StockLedgerEntryIdVO
    position_id: StockPositionIdVO
    layer_id: ValuationLayerIdVO
    inventory_item_id: InventoryItemIdVO
    owner_id: StockOwnerIdVO
    warehouse_id: WarehouseIdVO
    base_uom: UomCodeVO
    quantity_delta: StockDeltaVO
    cost_delta: MoneyVO

    @classmethod
    def create(
        cls,
        *,
        identifier: ValuationEntryIdVO,
        ledger_entry_id: StockLedgerEntryIdVO,
        position_id: StockPositionIdVO,
        layer_id: ValuationLayerIdVO,
        inventory_item_id: InventoryItemIdVO,
        owner_id: StockOwnerIdVO,
        warehouse_id: WarehouseIdVO,
        base_uom: UomCodeVO,
        quantity_delta: StockDeltaVO,
        cost_delta: MoneyVO,
    ) -> Self:
        """Создаёт положительную запись первоначальной стоимости без вычисления цены единицы."""
        return cls.restore(
            identifier=identifier,
            ledger_entry_id=ledger_entry_id,
            position_id=position_id,
            layer_id=layer_id,
            inventory_item_id=inventory_item_id,
            owner_id=owner_id,
            warehouse_id=warehouse_id,
            base_uom=base_uom,
            quantity_delta=quantity_delta,
            cost_delta=cost_delta,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: ValuationEntryIdVO,
        ledger_entry_id: StockLedgerEntryIdVO,
        position_id: StockPositionIdVO,
        layer_id: ValuationLayerIdVO,
        inventory_item_id: InventoryItemIdVO,
        owner_id: StockOwnerIdVO,
        warehouse_id: WarehouseIdVO,
        base_uom: UomCodeVO,
        quantity_delta: StockDeltaVO,
        cost_delta: MoneyVO,
    ) -> Self:
        """Восстанавливает все собственные поля записи без чтения слоя и физического журнала."""
        entry = cls(
            identifier,
            ledger_entry_id,
            position_id,
            layer_id,
            inventory_item_id,
            owner_id,
            warehouse_id,
            base_uom,
            quantity_delta,
            cost_delta,
        )
        entry.ensure_valid()
        return entry

    def ensure_valid(self) -> None:
        """Требует номинальные ссылки, конечное положительное количество и сохранённую неотрицательную стоимость."""
        if (
            not isinstance(self.id, ValuationEntryIdVO)
            or not isinstance(self.ledger_entry_id, StockLedgerEntryIdVO)
            or not isinstance(self.position_id, StockPositionIdVO)
            or not isinstance(self.layer_id, ValuationLayerIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity_delta, StockDeltaVO)
            or not isinstance(self.quantity_delta.value, Decimal)
            or not self.quantity_delta.value.is_finite()
            or self.quantity_delta.value <= 0
            or not isinstance(self.cost_delta, MoneyVO)
            or not isinstance(self.cost_delta.amount, Decimal)
            or not self.cost_delta.amount.is_finite()
            or self.cost_delta.amount < 0
        ):
            raise InvalidValuationEntryError(
                "Нужны номинальные поля положительной записи первоначальной стоимости."
            )
        get_uom(self.base_uom)
        if MoneyVO(self.cost_delta.amount, self.cost_delta.currency) != self.cost_delta:
            raise InvalidValuationEntryError(
                "Стоимость записи должна соответствовать сохранённой точности MoneyVO."
            )
