from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.stock_document.status_change_error import (
    InvalidStockStatusChangeError,
)


class StockStatusTransitionPolicy:
    """Разрешает все двенадцать направленных переходов между разными состояниями."""

    @staticmethod
    def allowed_targets(source: StockStatus) -> tuple[StockStatus, ...]:
        """Возвращает явную матрицу без перехода в то же состояние."""
        matrix = {
            StockStatus.SELLABLE: (
                StockStatus.QUARANTINE,
                StockStatus.DAMAGED,
                StockStatus.BLOCKED,
            ),
            StockStatus.QUARANTINE: (
                StockStatus.SELLABLE,
                StockStatus.DAMAGED,
                StockStatus.BLOCKED,
            ),
            StockStatus.DAMAGED: (
                StockStatus.SELLABLE,
                StockStatus.QUARANTINE,
                StockStatus.BLOCKED,
            ),
            StockStatus.BLOCKED: (
                StockStatus.SELLABLE,
                StockStatus.QUARANTINE,
                StockStatus.DAMAGED,
            ),
        }
        if not isinstance(source, StockStatus):
            raise InvalidStockStatusChangeError(
                "Нужно типизированное исходное состояние."
            )
        return matrix[source]

    @staticmethod
    def ensure_allowed(source: StockStatus, destination: StockStatus) -> None:
        """Запрещает прежнее или неизвестное целевое состояние."""
        if not isinstance(
            destination, StockStatus
        ) or destination not in StockStatusTransitionPolicy.allowed_targets(source):
            raise InvalidStockStatusChangeError(
                "Переход требует другое допустимое состояние запаса."
            )
