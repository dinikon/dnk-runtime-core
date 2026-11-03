from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionDocumentSnapshotError,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class ExecutedDocumentLineQuantityVO:
    """Суммирует фактическое количество одной конкретной плановой строки для регистрации."""

    document_line_id: StockDocumentLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO

    def __post_init__(self) -> None:
        """Требует типизированные ссылки, известную единицу и положительное количество."""
        if (
            not isinstance(self.document_line_id, StockDocumentLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
        ):
            raise InvalidStockExecutionDocumentSnapshotError(
                "Нужны типизированные ссылки и положительное исполненное количество строки."
            )
        get_uom(self.base_uom)
