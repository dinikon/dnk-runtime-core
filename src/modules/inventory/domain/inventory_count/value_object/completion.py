from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_count.error import (
    InventoryCountCompletionError,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)


@dataclass(frozen=True, slots=True)
class InventoryCountCompletionVO:
    """Хранит момент завершения и компактную согласованную цепочку ссылок либо отсутствие корректировки."""

    completed_at: datetime
    document_id: StockDocumentIdVO | None
    document_version: int | None
    execution_id: StockExecutionIdVO | None
    posting_id: StockPostingIdVO | None

    def __post_init__(self) -> None:
        """Нормализует момент в UTC и проверяет локальную матрицу всех ссылок без загрузки фактов."""
        object.__setattr__(
            self, "completed_at", normalize_inventory_count_time(self.completed_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует все ссылки и строгую версию документа вместе либо их полное отсутствие."""
        normalize_inventory_count_time(self.completed_at)
        if self.completed_at.utcoffset() != timedelta(0):
            raise InventoryCountCompletionError(
                "Момент завершения должен храниться в UTC."
            )
        values = (
            self.document_id,
            self.document_version,
            self.execution_id,
            self.posting_id,
        )
        if all(value is None for value in values):
            return
        if (
            not isinstance(self.document_id, StockDocumentIdVO)
            or type(self.document_version) is not int
            or self.document_version < 1
            or not isinstance(self.execution_id, StockExecutionIdVO)
            or not isinstance(self.posting_id, StockPostingIdVO)
        ):
            raise InventoryCountCompletionError(
                "Нужны все ссылки цепочки и положительная целая версия документа без bool либо все None."
            )
