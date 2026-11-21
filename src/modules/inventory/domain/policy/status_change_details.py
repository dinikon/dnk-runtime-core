from src.modules.inventory.domain.stock_document.value_object.status_change_details import (
    StockStatusChangeDetailsVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.status_change_error import (
    InvalidStockStatusChangeError,
)


class StatusChangeDetailsPolicy:
    """Согласует параметры STATUS_CHANGE между планом и его фактическими снимками."""

    @staticmethod
    def ensure_compatible(
        operation_type: StockOperationType, details: StockStatusChangeDetailsVO | None
    ) -> None:
        """Требует параметры именно для STATUS_CHANGE и запрещает их другим операциям."""
        if operation_type is StockOperationType.STATUS_CHANGE:
            if not isinstance(details, StockStatusChangeDetailsVO):
                raise InvalidStockStatusChangeError(
                    "Для изменения состояния нужны цель и причина."
                )
        elif details is not None:
            raise InvalidStockStatusChangeError(
                "Параметры изменения состояния принадлежат только STATUS_CHANGE."
            )
