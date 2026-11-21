from dataclasses import dataclass

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)


@dataclass(frozen=True, slots=True)
class StockAdjustmentExecutionLineBindingVO:
    """Назначает явные ID фактической строки и позиции каждой строке корректировки."""

    document_line_id: StockDocumentLineIdVO
    execution_line_id: StockExecutionLineIdVO
    position_id: StockPositionIdVO

    def __post_init__(self) -> None:
        """Требует типизированные идентификаторы без генерации и доступа к хранилищу."""
        if (
            not isinstance(self.document_line_id, StockDocumentLineIdVO)
            or not isinstance(self.execution_line_id, StockExecutionLineIdVO)
            or not isinstance(self.position_id, StockPositionIdVO)
        ):
            raise StockAdjustmentError(
                "Нужны ID строки документа, исполнения и физической позиции."
            )
