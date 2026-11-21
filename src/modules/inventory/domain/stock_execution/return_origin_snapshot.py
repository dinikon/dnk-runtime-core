from src.modules.inventory.domain.stock_document.return_error import (
    InvalidStockReturnError,
)
from dataclasses import dataclass
from datetime import datetime
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO


@dataclass(frozen=True, slots=True)
class StockReturnOriginLineSnapshot:
    """Передаёт идентичность и исходное количество одной фактической строки."""

    id: StockExecutionLineIdVO
    dimensions: StockDimensionsVO
    quantity: QuantityVO
    base_uom: UomCodeVO

    def ensure_valid(self) -> None:
        """Требует типизированную фактическую строку с положительным количеством."""
        if (
            not isinstance(self.id, StockExecutionLineIdVO)
            or not isinstance(self.dimensions, StockDimensionsVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value <= 0
            or not isinstance(self.base_uom, UomCodeVO)
        ):
            raise InvalidStockReturnError(
                "Нужна корректная исходная фактическая строка."
            )


@dataclass(frozen=True, slots=True)
class StockReturnOriginSnapshot:
    """Передаёт неизменяемое основание и признаки допустимости без ORM или чужого корня."""

    id: StockExecutionIdVO
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    posting_id: StockPostingIdVO | None
    is_compensated: bool
    document_source: DocumentSourceVO | None
    lines: tuple[StockReturnOriginLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет полный снимок основания и согласованность владельца всех строк."""
        if (
            not isinstance(self.id, StockExecutionIdVO)
            or not isinstance(self.operation_type, StockOperationType)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() is None
            or not isinstance(self.is_compensated, bool)
            or (
                self.posting_id is not None
                and not isinstance(self.posting_id, StockPostingIdVO)
            )
            or (
                self.document_source is not None
                and not isinstance(self.document_source, DocumentSourceVO)
            )
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidStockReturnError(
                "Нужен полный типизированный снимок исходного исполнения."
            )
        for line in self.lines:
            if not isinstance(line, StockReturnOriginLineSnapshot):
                raise InvalidStockReturnError(
                    "Нужны снимки исходных фактических строк."
                )
            line.ensure_valid()
            if line.dimensions.owner_id != self.owner_id:
                raise InvalidStockReturnError(
                    "Владелец исходной строки не совпадает с исполнением."
                )


@dataclass(frozen=True, slots=True)
class StockReturnUsageSnapshot:
    """Передаёт накопленное фактическое количество возврата по исходной строке."""

    origin_line_id: StockExecutionLineIdVO
    returned_quantity: QuantityVO

    def ensure_valid(self) -> None:
        """Допускает нулевой возврат только для типизированной исходной строки."""
        if not isinstance(
            self.origin_line_id, StockExecutionLineIdVO
        ) or not isinstance(self.returned_quantity, QuantityVO):
            raise InvalidStockReturnError(
                "Нужен корректный снимок накопленного возврата."
            )


@dataclass(frozen=True, slots=True)
class StockReturnFactSnapshot:
    """Передаёт исходную строку и неизменяемую физическую идентичность нового возврата."""

    origin_line_id: StockExecutionLineIdVO
    dimensions: StockDimensionsVO
    quantity: QuantityVO
    base_uom: UomCodeVO

    def ensure_valid(self) -> None:
        """Требует положительный факт с типизированной ссылкой и измерениями."""
        if (
            not isinstance(self.origin_line_id, StockExecutionLineIdVO)
            or not isinstance(self.dimensions, StockDimensionsVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value <= 0
            or not isinstance(self.base_uom, UomCodeVO)
        ):
            raise InvalidStockReturnError("Нужен корректный факт возврата.")
