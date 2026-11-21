from dataclasses import dataclass
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.stock_document.value_object.status_change_reason import (
    StatusChangeReasonVO,
)
from src.modules.inventory.domain.stock_document.status_change_error import (
    InvalidStockStatusChangeError,
)


@dataclass(frozen=True, slots=True)
class StockStatusChangeDetailsVO:
    """Фиксирует единое целевое состояние и причину документа или неизменяемого исполнения."""

    target_status: StockStatus
    reason: StatusChangeReasonVO

    def __post_init__(self) -> None:
        """Требует типизированное состояние и уже проверенный текст причины."""
        if not isinstance(self.target_status, StockStatus) or not isinstance(
            self.reason, StatusChangeReasonVO
        ):
            raise InvalidStockStatusChangeError(
                "Укажите целевое состояние и причину перехода."
            )
