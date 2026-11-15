from dataclasses import dataclass
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionValueError,
)


@dataclass(frozen=True, slots=True)
class ReceiptCostAllocationVO:
    """Связывает часть исходной суммы с собственной фактической строкой."""

    execution_line_id: StockExecutionLineIdVO
    amount: MoneyVO

    def __post_init__(self) -> None:
        """Проверяет собственную идентичность, валюту и неотрицательную сумму."""
        if (
            not isinstance(self.execution_line_id, StockExecutionLineIdVO)
            or not isinstance(self.amount, MoneyVO)
            or self.amount.amount < 0
        ):
            raise InvalidStockExecutionValueError(
                "Нужны строка исполнения и неотрицательная сумма распределения."
            )
