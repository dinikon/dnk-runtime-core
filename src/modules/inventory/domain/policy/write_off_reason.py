from src.modules.inventory.domain.stock_document.value_object.write_off_reason import (
    WriteOffReasonVO,
)
from src.modules.inventory.domain.stock_document.write_off_error import (
    InvalidWriteOffReasonError,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)


class WriteOffReasonPolicy:
    """Согласует обязательное основание списания в документе и его неизменяемых фактах."""

    @staticmethod
    def ensure_compatible(
        operation_type: StockOperationType, reason: WriteOffReasonVO | None
    ) -> None:
        """Требует типизированную причину только для WRITE_OFF; остальные операции её не принимают."""
        if operation_type is StockOperationType.WRITE_OFF:
            if not isinstance(reason, WriteOffReasonVO):
                raise InvalidWriteOffReasonError("Для списания обязательна причина.")
        elif reason is not None:
            raise InvalidWriteOffReasonError(
                "Причина списания допустима только для WRITE_OFF."
            )
