from dataclasses import dataclass

from src.modules.inventory.domain.stock_document.error import (
    InvalidStockTransferReceiptDocumentLineBindingError,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)


@dataclass(frozen=True, slots=True)
class StockTransferReceiptDocumentLineBindingVO:
    """Назначает строке перемещения явно переданные новые ID строк расхода T и прихода B."""

    transfer_line_id: StockTransferLineIdVO
    issue_document_line_id: StockDocumentLineIdVO
    receipt_document_line_id: StockDocumentLineIdVO

    def __post_init__(self) -> None:
        """Проверяет типы ссылок и различие новых ID без генерации идентичности в Domain."""
        if (
            not isinstance(self.transfer_line_id, StockTransferLineIdVO)
            or not isinstance(self.issue_document_line_id, StockDocumentLineIdVO)
            or not isinstance(self.receipt_document_line_id, StockDocumentLineIdVO)
            or self.issue_document_line_id == self.receipt_document_line_id
        ):
            raise InvalidStockTransferReceiptDocumentLineBindingError(
                "Нужны типизированные ID основания и разные ID строк обеих сторон."
            )
