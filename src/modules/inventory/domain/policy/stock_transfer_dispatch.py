from src.modules.inventory.domain.policy.stock_transfer_execution_grouping import (
    StockTransferExecutionGroupingPolicy,
)
from src.modules.inventory.domain.policy.location_availability import (
    LocationAvailabilityPolicy,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_confirmation import (
    StockTransferConfirmationPolicy,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferSnapshotError,
)
from src.modules.inventory.domain.stock_execution.transfer_snapshot import (
    StockExecutionTransferSnapshot,
)
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_transfer.dispatch_plan_snapshot import (
    StockTransferDispatchPlanSnapshot,
)
from src.modules.inventory.domain.stock_transfer.dispatch_snapshot import (
    StockTransferDispatchedLineSnapshot,
    StockTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferDispatchPlanSnapshotError,
    InvalidStockTransferDispatchSnapshotError,
    InvalidStockTransferTransitError,
    StockTransferDispatchMismatchError,
    StockTransferDispatchQuantityExceededError,
    StockTransferStatusError,
    StockTransferTimeError,
    StockTransferTransitMismatchError,
    StockTransferVersionConflictError,
    UnbalancedStockTransferDispatchError,
)
from src.modules.inventory.domain.stock_transfer.value_object.execution_binding import (
    StockTransferExecutionBindingVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.stock_transfer.value_object.transit import (
    StockTransferTransitVO,
)
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class StockTransferDispatchPolicy:
    """Согласует расход исходного склада и приход в транзит без изменения запасов или других корней."""

    @staticmethod
    def build_dispatch(
        *,
        transfer: StockTransferDispatchPlanSnapshot,
        issue: StockExecutionTransferSnapshot,
        receipt: StockExecutionTransferSnapshot,
        transit: StockTransferTransitVO,
        source_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
        transit_warehouse: WarehouseSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
        issue_bindings: tuple[StockTransferExecutionBindingVO, ...],
        receipt_bindings: tuple[StockTransferExecutionBindingVO, ...],
    ) -> StockTransferDispatchSnapshot:
        """Проверяет всю пару, точно балансирует сохраняемые измерения и строит одну регистрацию по версии плана."""
        if not isinstance(transfer, StockTransferDispatchPlanSnapshot):
            raise InvalidStockTransferDispatchPlanSnapshotError(
                "Нужен текущий снимок плана отправки."
            )
        transfer.ensure_valid()
        if transfer.status not in (
            StockTransferStatus.CONFIRMED,
            StockTransferStatus.IN_PROGRESS,
        ):
            raise StockTransferStatusError(
                "Отправка доступна подтверждённому или исполняемому перемещению."
            )
        for execution in (issue, receipt):
            if not isinstance(execution, StockExecutionTransferSnapshot):
                raise InvalidStockExecutionTransferSnapshotError(
                    "Нужны специализированные снимки расхода и прихода."
                )
            execution.ensure_valid()
        if not isinstance(transit, StockTransferTransitVO):
            raise InvalidStockTransferTransitError(
                "Нужен транзитный маршрут перемещения."
            )
        if transit.warehouse_id in (
            transfer.source_warehouse_id,
            transfer.destination_warehouse_id,
        ) or (transfer.transit is not None and transfer.transit != transit):
            raise StockTransferTransitMismatchError(
                "Транзит должен быть отдельным и совпадать с ранее зафиксированным маршрутом."
            )
        StockTransferConfirmationPolicy.ensure_warehouses(
            source_warehouse_id=transfer.source_warehouse_id,
            destination_warehouse_id=transfer.destination_warehouse_id,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
        )
        if not isinstance(transit_warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок транзитного склада.")
        transit_warehouse.ensure_valid()
        if transit_warehouse.id != transit.warehouse_id:
            raise StockTransferTransitMismatchError(
                "Снимок транзитного склада не соответствует маршруту."
            )
        if (
            issue.operation_type is not StockOperationType.ISSUE
            or receipt.operation_type is not StockOperationType.RECEIPT
            or issue.id == receipt.id
            or issue.warehouse_id != transfer.source_warehouse_id
            or receipt.warehouse_id != transit.warehouse_id
            or issue.owner_id != transfer.owner_id
            or receipt.owner_id != transfer.owner_id
            or {line.id for line in issue.lines}.intersection(
                line.id for line in receipt.lines
            )
        ):
            raise StockTransferDispatchMismatchError(
                "Нужны разные ISSUE из исходного склада и RECEIPT в транзит одного владельца с разными фактическими ID."
            )
        if issue.executed_at != receipt.executed_at:
            raise StockTransferTimeError(
                "Расход и приход в транзит должны иметь одно время фактической отправки."
            )
        if not isinstance(locations, tuple):
            raise InvalidStockLocationSnapshotError(
                "Нужен tuple снимков фактических локаций пары."
            )
        by_location = {}
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidStockLocationSnapshotError(
                    "Нужны снимки локаций пары отправки."
                )
            location.ensure_valid()
            if location.id in by_location:
                raise StockTransferDispatchMismatchError(
                    "Снимки локаций не должны повторяться."
                )
            by_location[location.id] = location
        if set(by_location) != {
            line.dimensions.location_id
            for execution in (issue, receipt)
            for line in execution.lines
        }:
            raise StockTransferDispatchMismatchError(
                "Нужны ровно участвующие снимки локаций без пропусков и лишних."
            )
        for line in issue.lines:
            LocationAvailabilityPolicy.ensure_available(
                location=by_location[line.dimensions.location_id],
                warehouse=source_warehouse,
            )
        for line in receipt.lines:
            location = by_location[line.dimensions.location_id]
            if (
                location.id != transit.location_id
                or location.location_type is not LocationType.TRANSIT
            ):
                raise StockTransferTransitMismatchError(
                    "Весь приход должен поступать в выбранную локацию TRANSIT."
                )
            LocationAvailabilityPolicy.ensure_available(
                location=location, warehouse=transit_warehouse
            )
        plan = {line.id: line for line in transfer.lines}
        outgoing, quantities, issue_ids = StockTransferExecutionGroupingPolicy.group(
            issue, issue_bindings, plan, StockTransferDispatchMismatchError
        )
        incoming, _, receipt_ids = StockTransferExecutionGroupingPolicy.group(
            receipt, receipt_bindings, plan, StockTransferDispatchMismatchError
        )
        if outgoing != incoming:
            raise UnbalancedStockTransferDispatchError(
                "Расход и приход должны совпадать по строке, товару, владельцу, LOT/SERIAL, состоянию и единице."
            )
        dispatch = StockTransferDispatchSnapshot(
            transfer.id,
            transfer.version,
            transfer.source_warehouse_id,
            transfer.destination_warehouse_id,
            transfer.owner_id,
            transit,
            issue.id,
            receipt.id,
            issue.executed_at,
            tuple(
                StockTransferDispatchedLineSnapshot(
                    identifier,
                    plan[identifier].inventory_item_id,
                    plan[identifier].base_uom,
                    quantities[identifier],
                    issue_ids[identifier],
                    receipt_ids[identifier],
                )
                for identifier in sorted(quantities, key=lambda value: value.uuid.int)
            ),
        )
        StockTransferDispatchPolicy.ensure_compatible(
            transfer=transfer, dispatch=dispatch
        )
        return dispatch

    @staticmethod
    def ensure_compatible(
        *,
        transfer: StockTransferDispatchPlanSnapshot,
        dispatch: StockTransferDispatchSnapshot,
    ) -> None:
        """Повторно проверяет цель, версию, состояние, фиксированный транзит, хронологию и предел отправки."""
        if not isinstance(transfer, StockTransferDispatchPlanSnapshot):
            raise InvalidStockTransferDispatchPlanSnapshotError(
                "Нужен снимок текущего плана отправки."
            )
        transfer.ensure_valid()
        if not isinstance(dispatch, StockTransferDispatchSnapshot):
            raise InvalidStockTransferDispatchSnapshotError(
                "Нужен результат согласованной отправки."
            )
        dispatch.ensure_valid()
        if transfer.status not in (
            StockTransferStatus.CONFIRMED,
            StockTransferStatus.IN_PROGRESS,
        ):
            raise StockTransferStatusError(
                "Регистрировать отправку можно только после подтверждения перемещения."
            )
        if dispatch.transfer_version != transfer.version:
            raise StockTransferVersionConflictError(
                "Отправка построена по другой версии StockTransfer."
            )
        if (
            dispatch.transfer_id != transfer.id
            or dispatch.source_warehouse_id != transfer.source_warehouse_id
            or dispatch.destination_warehouse_id != transfer.destination_warehouse_id
            or dispatch.owner_id != transfer.owner_id
        ):
            raise StockTransferDispatchMismatchError(
                "Отправка относится к другому перемещению, направлению или владельцу."
            )
        if transfer.transit is not None and transfer.transit != dispatch.transit:
            raise StockTransferTransitMismatchError(
                "Маршрут уже зафиксирован первой отправкой."
            )
        if dispatch.executed_at < transfer.updated_at:
            raise StockTransferTimeError(
                "Отправка не может предшествовать текущему состоянию перемещения."
            )
        by_line = {line.id: line for line in transfer.lines}
        for line in dispatch.lines:
            planned = by_line.get(line.transfer_line_id)
            if (
                planned is None
                or line.inventory_item_id != planned.inventory_item_id
                or line.base_uom != planned.base_uom
            ):
                raise StockTransferDispatchMismatchError(
                    "Строка, товар и единица отправки не соответствуют плану."
                )
            if (
                QuantityArithmeticPolicy.add(
                    planned.dispatched_qty, line.quantity
                ).value
                > planned.planned_qty.value
            ):
                raise StockTransferDispatchQuantityExceededError(
                    "Отправка превышает оставшийся план строки."
                )
