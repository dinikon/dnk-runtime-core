from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerReceiptSnapshotError,
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


@dataclass(frozen=True, slots=True)
class ValuationLayerReceiptSnapshot:
    """Передаёт первоначальное основание слоя без изменяемых остатков и версии потребления."""

    id: ValuationLayerIdVO
    source: ValuationLayerSourceVO
    inventory_item_id: InventoryItemIdVO
    owner_id: StockOwnerIdVO
    warehouse_id: WarehouseIdVO
    base_uom: UomCodeVO
    cost_basis: CostBasisVO
    received_at: datetime
    created_at: datetime

    def ensure_valid(self) -> None:
        """Проверяет собственные номинальные поля, стоимость и сохранённую UTC-хронологию прихода."""
        if (
            not isinstance(self.id, ValuationLayerIdVO)
            or not isinstance(self.source, ValuationLayerSourceVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.cost_basis, CostBasisVO)
        ):
            raise InvalidValuationLayerReceiptSnapshotError(
                "Нужны типизированные поля первоначального основания слоя."
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
            raise InvalidValuationLayerReceiptSnapshotError(
                "Снимок хранит UTC-время регистрации не раньше прихода."
            )
