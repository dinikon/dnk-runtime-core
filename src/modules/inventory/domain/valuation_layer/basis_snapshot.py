from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerBasisSnapshotError,
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
from src.modules.inventory.domain.valuation_layer.value_object.transfer_origin import (
    ValuationLayerTransferOriginVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class ValuationLayerBasisSnapshot:
    """Хранит исходную оценку, FIFO-дату и основание формирования стоимостного слоя."""

    id: ValuationLayerIdVO
    source: ValuationLayerSourceVO
    inventory_item_id: InventoryItemIdVO
    owner_id: StockOwnerIdVO
    warehouse_id: WarehouseIdVO
    base_uom: UomCodeVO
    cost_basis: CostBasisVO
    received_at: datetime
    created_at: datetime
    transfer_origin: ValuationLayerTransferOriginVO | None = None

    @property
    def available_at(self) -> datetime:
        """Возвращает физическую дату появления стоимости на позиции слоя."""
        if self.transfer_origin is None:
            return self.received_at
        return self.transfer_origin.moved_at

    def ensure_valid(self) -> None:
        """Проверяет собственные поля, происхождение и порядок дат слоя."""
        if (
            not isinstance(self.id, ValuationLayerIdVO)
            or not isinstance(self.source, ValuationLayerSourceVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.cost_basis, CostBasisVO)
        ):
            raise InvalidValuationLayerBasisSnapshotError(
                "Нужны типизированные поля первоначального основания слоя."
            )
        self.source.ensure_valid()
        self.cost_basis.ensure_valid()
        get_uom(self.base_uom)
        if self.transfer_origin is not None:
            self._ensure_transfer_origin(self.transfer_origin)
        normalize_valuation_time(self.received_at)
        normalize_valuation_time(self.created_at)
        if (
            self.received_at.utcoffset() != timedelta(0)
            or self.created_at.utcoffset() != timedelta(0)
            or not self.received_at <= self.available_at <= self.created_at
        ):
            raise ValuationLayerTimeError(
                "Даты слоя хранятся в UTC: FIFO-дата <= доступность <= регистрация."
            )

    def _ensure_transfer_origin(self, origin: ValuationLayerTransferOriginVO) -> None:
        """Связывает производный слой с отдельным исходным слоем и другой позицией."""
        if not isinstance(origin, ValuationLayerTransferOriginVO):
            raise InvalidValuationLayerBasisSnapshotError(
                "Производному слою нужно типизированное происхождение переноса."
            )
        origin.ensure_valid()
        if (
            self.id == origin.parent_layer_id
            or self.source.posting_id == origin.receipt_source.posting_id
            or self.source.position_id == origin.receipt_source.position_id
            or self.source.ledger_entry_id == origin.outgoing_entry_id
        ):
            raise InvalidValuationLayerBasisSnapshotError(
                "Производный слой требует отдельного ID, пары записей и новой позиции."
            )
