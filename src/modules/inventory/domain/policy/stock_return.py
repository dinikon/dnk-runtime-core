from src.modules.inventory.domain.stock_execution.return_origin_snapshot import (
    StockReturnFactSnapshot,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidStockReturnError,
    StockReturnLimitError,
)
from src.modules.inventory.domain.stock_document.value_object.return_direction import (
    ReturnDirection,
)
from src.modules.inventory.domain.stock_document.value_object.return_details import (
    StockReturnDetailsVO,
)
from src.modules.inventory.domain.stock_execution.return_origin_snapshot import (
    StockReturnOriginSnapshot,
    StockReturnOriginLineSnapshot,
    StockReturnUsageSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from decimal import Decimal


class StockReturnPolicy:
    """Проверяет происхождение и общий лимит возвратов независимо от SQL и транспорта."""

    @staticmethod
    def direction(origin: StockReturnOriginSnapshot) -> ReturnDirection:
        """Допускает только проведённые ручные RECEIPT/ISSUE без компенсации."""
        if not isinstance(origin, StockReturnOriginSnapshot):
            raise InvalidStockReturnError("Нужен снимок исходного исполнения.")
        origin.ensure_valid()
        if (
            not isinstance(origin, StockReturnOriginSnapshot)
            or origin.posting_id is None
            or origin.is_compensated
            or origin.document_source is not None
            or origin.operation_type
            not in (StockOperationType.RECEIPT, StockOperationType.ISSUE)
            or not origin.lines
        ):
            raise InvalidStockReturnError(
                "Возврат требует проведённое ручное поступление или расход без компенсации."
            )
        if len({line.id for line in origin.lines}) != len(origin.lines):
            raise InvalidStockReturnError(
                "Строки основания должны иметь уникальные ID."
            )
        return (
            ReturnDirection.FROM_RECIPIENT
            if origin.operation_type is StockOperationType.ISSUE
            else ReturnDirection.TO_SUPPLIER
        )

    @staticmethod
    def ensure_details(
        details: StockReturnDetailsVO, origin: StockReturnOriginSnapshot
    ) -> None:
        """Сверяет замороженное основание с действительным направлением исходного факта."""
        if (
            details.origin_execution_id != origin.id
            or details.direction is not StockReturnPolicy.direction(origin)
        ):
            raise InvalidStockReturnError(
                "Направление и основание возврата не совпадают с исходным фактом."
            )

    @staticmethod
    def line(
        origin: StockReturnOriginSnapshot, identifier: StockExecutionLineIdVO
    ) -> StockReturnOriginLineSnapshot:
        """Выбирает строку только внутри полного исходного исполнения."""
        for line in origin.lines:
            if line.id == identifier:
                return line
        raise InvalidStockReturnError("Строка не принадлежит исходному исполнению.")

    @staticmethod
    def ensure_limit(
        origin: StockReturnOriginSnapshot,
        usage: tuple[StockReturnUsageSnapshot, ...],
        requested: tuple[tuple[StockExecutionLineIdVO, QuantityVO], ...],
    ) -> None:
        """Суммирует все распределения одной исходной строки и сверяет точный общий лимит."""
        StockReturnPolicy.direction(origin)
        if not isinstance(usage, tuple):
            raise InvalidStockReturnError("Нужен полный неизменяемый снимок возвратов.")
        for entry in usage:
            if not isinstance(entry, StockReturnUsageSnapshot):
                raise InvalidStockReturnError("Нужны снимки накопленных возвратов.")
            entry.ensure_valid()
        used = {v.origin_line_id: v.returned_quantity for v in usage}
        if len(used) != len(usage) or set(used) != {v.id for v in origin.lines}:
            raise InvalidStockReturnError("Нужен полный снимок накопленных возвратов.")
        grouped: dict[StockExecutionLineIdVO, QuantityVO] = {}
        for identifier, quantity in requested:
            StockReturnPolicy.line(origin, identifier)
            grouped[identifier] = QuantityArithmeticPolicy.add(
                grouped.get(identifier, QuantityVO(Decimal(0))), quantity
            )
        for identifier, quantity in grouped.items():
            source = StockReturnPolicy.line(origin, identifier)
            if used[identifier].value > source.quantity.value:
                raise InvalidStockReturnError(
                    "История возвратов превышает исходный факт."
                )
            remaining = QuantityArithmeticPolicy.subtract(
                source.quantity, used[identifier]
            )
            if quantity.value > remaining.value:
                raise StockReturnLimitError(
                    "Превышен остаток к возврату по исходной строке.",
                    origin_line_id=identifier,
                    requested=quantity,
                    remaining=remaining,
                )

    @staticmethod
    def ensure_plan(
        *,
        details: StockReturnDetailsVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        lines: tuple[StockDocumentLine, ...],
        origin: StockReturnOriginSnapshot,
        usage: tuple[StockReturnUsageSnapshot, ...],
    ) -> None:
        """Проверяет замороженное основание и каждую строку всего плана без резервирования лимита."""
        StockReturnPolicy.ensure_details(details, origin)
        if (warehouse_id, owner_id) != (origin.warehouse_id, origin.owner_id):
            raise InvalidStockReturnError("Склад и владелец наследуются из основания.")
        requested = []
        for line in lines:
            if line.return_origin_line_id is None:
                raise InvalidStockReturnError(
                    "Строка возврата требует фактическое основание."
                )
            source = StockReturnPolicy.line(origin, line.return_origin_line_id)
            if (line.inventory_item_id, line.base_uom) != (
                source.dimensions.inventory_item_id,
                source.base_uom,
            ):
                raise InvalidStockReturnError(
                    "Товар и единица строки не совпадают с основанием."
                )
            requested.append((source.id, line.planned_qty))
        StockReturnPolicy.ensure_limit(origin, usage, tuple(requested))

    @staticmethod
    def ensure_facts(
        *,
        details: StockReturnDetailsVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        facts: tuple[StockReturnFactSnapshot, ...],
        origin: StockReturnOriginSnapshot | None,
        usage: tuple[StockReturnUsageSnapshot, ...],
    ) -> None:
        """Повторно проверяет идентичность SKU/владельца/LOT/SERIAL и накопленный лимит факта."""
        if origin is None:
            raise InvalidStockReturnError(
                "Новое исполнение и проведение требуют полного основания возврата."
            )
        StockReturnPolicy.ensure_details(details, origin)
        if (warehouse_id, owner_id) != (origin.warehouse_id, origin.owner_id):
            raise InvalidStockReturnError(
                "Склад и владелец возврата не совпадают с основанием."
            )
        if not facts:
            raise InvalidStockReturnError("Возврат требует фактические строки.")
        for fact in facts:
            if not isinstance(fact, StockReturnFactSnapshot):
                raise InvalidStockReturnError("Нужны типизированные факты возврата.")
            fact.ensure_valid()
            source = StockReturnPolicy.line(origin, fact.origin_line_id)
            a, b = fact.dimensions, source.dimensions
            if (
                a.inventory_item_id,
                a.owner_id,
                a.lot_id,
                a.serial_id,
                fact.base_uom,
            ) != (
                b.inventory_item_id,
                b.owner_id,
                b.lot_id,
                b.serial_id,
                source.base_uom,
            ):
                raise InvalidStockReturnError(
                    "Нельзя подменить товар, владельца, партию, серию или базовую единицу возврата."
                )
        StockReturnPolicy.ensure_limit(
            origin, usage, tuple((f.origin_line_id, f.quantity) for f in facts)
        )
