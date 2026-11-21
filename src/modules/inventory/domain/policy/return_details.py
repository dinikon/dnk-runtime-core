from src.modules.inventory.domain.stock_document.value_object.return_details import (
    StockReturnDetailsVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidStockReturnError,
)


class ReturnDetailsPolicy:
    """Согласует собственные реквизиты RETURN с типом операции."""

    @staticmethod
    def ensure_compatible(
        operation_type: StockOperationType, details: StockReturnDetailsVO | None
    ) -> None:
        """Требует реквизиты возврата только для RETURN."""
        if (operation_type is StockOperationType.RETURN) != isinstance(
            details, StockReturnDetailsVO
        ) or (details is not None and not isinstance(details, StockReturnDetailsVO)):
            raise InvalidStockReturnError(
                "Реквизиты возврата обязательны только для RETURN."
            )
