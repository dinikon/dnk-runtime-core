from dataclasses import dataclass

from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_posting.error import InvalidPostingSourceError


@dataclass(frozen=True, slots=True)
class PostingSourceVO:
    """Ссылается на исполнение, послужившее основанием проведения."""

    execution_id: StockExecutionIdVO

    def __post_init__(self) -> None:
        """Требует явную типизированную ссылку, не проверяя существование исполнения."""
        if not isinstance(self.execution_id, StockExecutionIdVO):
            raise InvalidPostingSourceError("Нужен StockExecutionIdVO основания.")
