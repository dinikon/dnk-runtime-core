from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferSnapshotError,
)
from src.modules.inventory.domain.stock_execution.transfer_snapshot import (
    StockExecutionTransferSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.dispatch_plan_snapshot import (
    StockTransferDispatchPlanLineSnapshot,
)
from src.modules.inventory.domain.stock_transfer.receipt_plan_snapshot import (
    StockTransferReceiptPlanLineSnapshot,
)
from src.modules.inventory.domain.stock_transfer.error import (
    StockTransferError,
    InvalidStockTransferExecutionBindingError,
)
from src.modules.inventory.domain.stock_transfer.value_object.execution_binding import (
    StockTransferExecutionBindingVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class StockTransferExecutionGroupingPolicy:
    """Группирует целые фактические строки пары без потери идентичности плановой строки и запасов."""

    @staticmethod
    def group(
        execution: StockExecutionTransferSnapshot,
        bindings: tuple[StockTransferExecutionBindingVO, ...],
        plan: dict[
            StockTransferLineIdVO,
            StockTransferDispatchPlanLineSnapshot
            | StockTransferReceiptPlanLineSnapshot,
        ],
        mismatch_error: type[StockTransferError],
    ) -> tuple[
        dict[tuple[object, ...], QuantityVO],
        dict[StockTransferLineIdVO, QuantityVO],
        dict[StockTransferLineIdVO, tuple[StockExecutionLineIdVO, ...]],
    ]:
        """Назначает все целые фактические строки и группирует без потери сохраняемых измерений."""
        if not isinstance(execution, StockExecutionTransferSnapshot):
            raise InvalidStockExecutionTransferSnapshotError(
                "Нужен снимок фактической стороны перемещения."
            )
        execution.ensure_valid()
        if not isinstance(mismatch_error, type) or not issubclass(
            mismatch_error, StockTransferError
        ):
            raise InvalidStockTransferExecutionBindingError(
                "Нужен тип доменной ошибки согласования пары."
            )
        if not isinstance(plan, dict):
            raise InvalidStockTransferExecutionBindingError(
                "Нужны снимки строк плана по их ID."
            )
        for identifier, row in plan.items():
            if not isinstance(
                row,
                (
                    StockTransferDispatchPlanLineSnapshot,
                    StockTransferReceiptPlanLineSnapshot,
                ),
            ):
                raise InvalidStockTransferExecutionBindingError(
                    "Нужны снимки плановых строк отправки или приёмки."
                )
            row.ensure_valid()
            if row.id != identifier:
                raise InvalidStockTransferExecutionBindingError(
                    "Ключ строки плана не соответствует её ID."
                )
        if not isinstance(bindings, tuple):
            raise InvalidStockTransferExecutionBindingError(
                "Назначения передаются в tuple."
            )
        selected = {}
        facts = {line.id: line for line in execution.lines}
        for binding in bindings:
            if not isinstance(binding, StockTransferExecutionBindingVO):
                raise InvalidStockTransferExecutionBindingError(
                    "Нужны StockTransferExecutionBindingVO."
                )
            if (
                binding.execution_line_id in selected
                or binding.execution_line_id not in facts
                or binding.transfer_line_id not in plan
            ):
                raise mismatch_error(
                    "Назначение требует известные ID и однократное использование фактической строки."
                )
            selected[binding.execution_line_id] = binding.transfer_line_id
        if set(selected) != set(facts):
            raise mismatch_error(
                "Все фактические строки стороны должны быть назначены без пропусков."
            )
        groups, quantities, ids = {}, {}, {}
        for identifier in sorted(facts, key=lambda value: value.uuid.int):
            line, target = facts[identifier], plan[selected[identifier]]
            if (
                line.inventory_item_id != target.inventory_item_id
                or line.base_uom != target.base_uom
            ):
                raise mismatch_error(
                    "Товар и единица факта не соответствуют строке перемещения."
                )
            dimensions = line.dimensions
            key = (
                target.id,
                dimensions.inventory_item_id,
                dimensions.owner_id,
                dimensions.lot_id,
                dimensions.serial_id,
                dimensions.stock_status,
                line.base_uom,
            )
            groups[key] = (
                line.quantity
                if key not in groups
                else QuantityArithmeticPolicy.add(groups[key], line.quantity)
            )
            quantities[target.id] = (
                line.quantity
                if target.id not in quantities
                else QuantityArithmeticPolicy.add(quantities[target.id], line.quantity)
            )
            ids.setdefault(target.id, []).append(identifier)
        return (
            groups,
            quantities,
            {identifier: tuple(values) for identifier, values in ids.items()},
        )
