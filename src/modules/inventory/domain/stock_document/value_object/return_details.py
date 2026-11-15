from dataclasses import dataclass
from src.modules.inventory.domain.stock_document.value_object.return_direction import (
    ReturnDirection,
)
from src.modules.inventory.domain.stock_document.value_object.return_reason import (
    ReturnReasonVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidStockReturnError,
)


@dataclass(frozen=True, slots=True)
class StockReturnDetailsVO:
    """Фиксирует основание, направление и причину документа либо неизменяемого факта."""

    origin_execution_id: StockExecutionIdVO
    direction: ReturnDirection
    reason: ReturnReasonVO

    def __post_init__(self) -> None:
        """Требует типизированную ссылку и проверенные реквизиты операции."""
        if (
            not isinstance(self.origin_execution_id, StockExecutionIdVO)
            or not isinstance(self.direction, ReturnDirection)
            or not isinstance(self.reason, ReturnReasonVO)
        ):
            raise InvalidStockReturnError(
                "Нужны исходное исполнение, направление и причина возврата."
            )
