from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_posting.receipt_valuation_snapshot import (
    StockReceiptValuationSnapshot,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerValueError,
    ValuationLayerTimeError,
)
from src.modules.inventory.domain.valuation_layer.time import normalize_valuation_time
from src.modules.inventory.domain.valuation_layer.value_object.cost_basis import (
    CostBasisVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.source import (
    ValuationLayerSourceVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class ValuationLayer:
    """Фиксирует первоначальную стоимость конкретного поступления без изменения физического запаса или расхода слоя."""

    id: ValuationLayerIdVO
    source: ValuationLayerSourceVO
    inventory_item_id: InventoryItemIdVO
    owner_id: StockOwnerIdVO
    warehouse_id: WarehouseIdVO
    base_uom: UomCodeVO
    cost_basis: CostBasisVO
    received_at: datetime
    created_at: datetime

    @classmethod
    def create_from_receipt(
        cls,
        *,
        identifier: ValuationLayerIdVO,
        receipt: StockReceiptValuationSnapshot,
        total_cost: MoneyVO,
        created_at: datetime,
    ) -> Self:
        """Выводит идентичность и количество из проверенного прихода, фиксируя явно переданную полную стоимость."""
        if not isinstance(receipt, StockReceiptValuationSnapshot):
            raise InvalidValuationLayerValueError(
                "Нужно специализированное основание StockReceiptValuationSnapshot."
            )
        receipt.ensure_valid()
        return cls.restore(
            identifier=identifier,
            source=ValuationLayerSourceVO(
                receipt.posting_id, receipt.ledger_entry_id, receipt.position_id
            ),
            inventory_item_id=receipt.inventory_item_id,
            owner_id=receipt.owner_id,
            warehouse_id=receipt.warehouse_id,
            base_uom=receipt.base_uom,
            cost_basis=CostBasisVO(receipt.quantity, total_cost),
            received_at=receipt.received_at,
            created_at=created_at,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: ValuationLayerIdVO,
        source: ValuationLayerSourceVO,
        inventory_item_id: InventoryItemIdVO,
        owner_id: StockOwnerIdVO,
        warehouse_id: WarehouseIdVO,
        base_uom: UomCodeVO,
        cost_basis: CostBasisVO,
        received_at: datetime,
        created_at: datetime,
    ) -> Self:
        """Восстанавливает все собственные исторические поля без чтения проведения, цен и текущих справочников."""
        layer = cls(
            identifier,
            source,
            inventory_item_id,
            owner_id,
            warehouse_id,
            base_uom,
            cost_basis,
            normalize_valuation_time(received_at),
            normalize_valuation_time(created_at),
        )
        layer._validate()
        return layer

    def _validate(self) -> None:
        """Проверяет собственные ссылки, стоимость, единицу и UTC-хронологию неизменяемого слоя."""
        if (
            not isinstance(self.id, ValuationLayerIdVO)
            or not isinstance(self.source, ValuationLayerSourceVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.cost_basis, CostBasisVO)
        ):
            raise InvalidValuationLayerValueError(
                "Нужны номинальные поля стоимостного слоя и CostBasisVO."
            )
        self.source.ensure_valid()
        self.cost_basis.ensure_valid()
        get_uom(self.base_uom)
        normalize_valuation_time(self.received_at)
        normalize_valuation_time(self.created_at)
        if (
            self.received_at.utcoffset() != timedelta(0)
            or self.created_at.utcoffset() != timedelta(0)
            or self.created_at < self.received_at
        ):
            raise ValuationLayerTimeError(
                "Даты слоя хранятся в UTC; регистрация не раньше исходного поступления."
            )
