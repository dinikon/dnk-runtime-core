from dataclasses import dataclass

from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.stock_document.error import (
    InvalidShipmentDocumentLineBindingError,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)


@dataclass(frozen=True, slots=True)
class ShipmentDocumentLineBindingVO:
    """Связывает оставшуюся строку отправления с явно переданным новым ID строки расходного документа."""

    shipment_line_id: ShipmentLineIdVO
    document_line_id: StockDocumentLineIdVO

    def __post_init__(self) -> None:
        """Проверяет типизированные ID без генерации идентичности внутри Domain."""
        if not isinstance(self.shipment_line_id, ShipmentLineIdVO) or not isinstance(
            self.document_line_id, StockDocumentLineIdVO
        ):
            raise InvalidShipmentDocumentLineBindingError(
                "Нужны ShipmentLineIdVO и StockDocumentLineIdVO."
            )
