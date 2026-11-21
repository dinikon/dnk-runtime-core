from dataclasses import dataclass

from src.modules.inventory.domain.count_sheet.value_object.identifier import (
    CountSheetIdVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.stock_document.error import (
    InventoryCountAdjustmentMismatchError,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)


@dataclass(frozen=True, slots=True)
class InventoryCountDocumentLineBindingVO:
    """Назначает новый ID строки документа составному источнику ведомость/строка."""

    document_line_id: StockDocumentLineIdVO
    sheet_id: CountSheetIdVO
    count_line_id: CountLineIdVO

    def __post_init__(self) -> None:
        """Требует типизированные идентификаторы без генерации ID внутри Domain."""
        if (
            not isinstance(self.document_line_id, StockDocumentLineIdVO)
            or not isinstance(self.sheet_id, CountSheetIdVO)
            or not isinstance(self.count_line_id, CountLineIdVO)
        ):
            raise InventoryCountAdjustmentMismatchError(
                "Нужны типизированные ID строки документа, ведомости и наблюдения."
            )
