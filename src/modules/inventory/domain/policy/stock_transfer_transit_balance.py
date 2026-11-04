from decimal import Decimal

from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_execution.transfer_snapshot import (
    StockExecutionTransferSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_transfer.dispatch_snapshot import (
    StockTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_transfer.receipt_snapshot import (
    StockTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_transfer.receipt_plan_snapshot import (
    StockTransferReceiptPlanSnapshot,
)
from src.modules.inventory.domain.stock_transfer.transit_balance_snapshot import (
    StockTransferTransitBalanceLineSnapshot,
    StockTransferTransitBalanceSnapshot,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferTransitBalanceError,
    StockTransferVersionConflictError,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class StockTransferTransitBalancePolicy:
    """Вычисляет состав транзита из переданной принятой истории, не обращаясь к хранилищу."""

    @staticmethod
    def build_balance(
        *,
        transfer: StockTransferReceiptPlanSnapshot,
        dispatches: tuple[StockTransferDispatchSnapshot, ...],
        receipts: tuple[StockTransferReceiptSnapshot, ...],
        executions: tuple[StockExecutionTransferSnapshot, ...],
    ) -> StockTransferTransitBalanceSnapshot:
        """Сверяет непрерывную историю версий и транзитные факты, затем точно вычитает приёмки по LOT/SERIAL."""
        if not isinstance(transfer, StockTransferReceiptPlanSnapshot):
            raise InvalidStockTransferTransitBalanceError(
                "Нужен снимок текущего прогресса приёмки."
            )
        transfer.ensure_valid()
        if transfer.status not in (
            StockTransferStatus.IN_PROGRESS,
            StockTransferStatus.COMPLETED,
        ):
            raise InvalidStockTransferTransitBalanceError(
                "Остаток транзита строится после начала отправки."
            )
        for values, expected_type in (
            (dispatches, StockTransferDispatchSnapshot),
            (receipts, StockTransferReceiptSnapshot),
            (executions, StockExecutionTransferSnapshot),
        ):
            if not isinstance(values, tuple) or not all(
                isinstance(value, expected_type) for value in values
            ):
                raise InvalidStockTransferTransitBalanceError(
                    "Нужны tuple принятых результатов и транзитных фактов."
                )
            for value in values:
                value.ensure_valid()
        events = sorted(
            (*dispatches, *receipts), key=lambda event: event.transfer_version
        )
        if not events or not isinstance(events[0], StockTransferDispatchSnapshot):
            raise InvalidStockTransferTransitBalanceError(
                "История начинается отправкой в транзит."
            )
        versions = [event.transfer_version for event in events]
        if (
            len(set(versions)) != len(versions)
            or versions[-1] != transfer.version - 1
            or len(versions) != transfer.version - versions[0]
        ):
            raise InvalidStockTransferTransitBalanceError(
                "История переходов должна быть непрерывной до текущей версии."
            )
        facts = {execution.id: execution for execution in executions}
        if len(facts) != len(executions):
            raise InvalidStockTransferTransitBalanceError(
                "Транзитные исполнения не должны повторяться."
            )
        plan = {line.id: line for line in transfer.lines}
        zero = QuantityVO(Decimal(0))
        sent, received, balance = {}, {}, {}
        execution_ids, line_ids, used_facts, sent_serials = set(), set(), set(), set()
        previous_time = events[0].executed_at
        for event in events:
            if (
                event.transfer_id != transfer.id
                or event.source_warehouse_id != transfer.source_warehouse_id
                or event.destination_warehouse_id != transfer.destination_warehouse_id
                or event.owner_id != transfer.owner_id
                or event.transit != transfer.transit
                or event.executed_at < previous_time
                or event.executed_at > transfer.updated_at
            ):
                raise InvalidStockTransferTransitBalanceError(
                    "История относится к другой области или нарушает хронологию."
                )
            previous_time = event.executed_at
            incoming = isinstance(event, StockTransferDispatchSnapshot)
            actual_id = (
                event.receipt_execution_id if incoming else event.issue_execution_id
            )
            execution = facts.get(actual_id)
            if (
                execution is None
                or execution.operation_type
                is not (
                    StockOperationType.RECEIPT if incoming else StockOperationType.ISSUE
                )
                or execution.warehouse_id != transfer.transit.warehouse_id
                or execution.owner_id != transfer.owner_id
                or execution.executed_at != event.executed_at
            ):
                raise InvalidStockTransferTransitBalanceError(
                    "Нужен соответствующий транзитный факт каждого принятого перехода."
                )
            ids = {event.issue_execution_id, event.receipt_execution_id}
            event_line_ids = {
                identifier
                for line in event.lines
                for identifier in (
                    *line.issue_execution_line_ids,
                    *line.receipt_execution_line_ids,
                )
            }
            if execution_ids.intersection(ids) or line_ids.intersection(event_line_ids):
                raise InvalidStockTransferTransitBalanceError(
                    "Исполнения и фактические строки нельзя учитывать повторно."
                )
            execution_ids.update(ids)
            line_ids.update(event_line_ids)
            used_facts.add(actual_id)
            actual_lines = {line.id: line for line in execution.lines}
            assigned = set()
            for row in event.lines:
                target = plan.get(row.transfer_line_id)
                if (
                    target is None
                    or target.inventory_item_id != row.inventory_item_id
                    or target.base_uom != row.base_uom
                ):
                    raise InvalidStockTransferTransitBalanceError(
                        "Строка истории не соответствует текущему плану."
                    )
                values = (
                    row.receipt_execution_line_ids
                    if incoming
                    else row.issue_execution_line_ids
                )
                total = zero
                for identifier in values:
                    actual = actual_lines.get(identifier)
                    if (
                        actual is None
                        or actual.inventory_item_id != row.inventory_item_id
                        or actual.base_uom != row.base_uom
                        or actual.dimensions.location_id != transfer.transit.location_id
                    ):
                        raise InvalidStockTransferTransitBalanceError(
                            "Состав факта не соответствует принятой строке и адресу транзита."
                        )
                    assigned.add(identifier)
                    total = QuantityArithmeticPolicy.add(total, actual.quantity)
                    key = (row.transfer_line_id, actual.dimensions, actual.base_uom)
                    available = balance.get(key, zero)
                    if incoming:
                        serial = actual.dimensions.serial_id
                        if serial is not None:
                            if serial in sent_serials:
                                raise InvalidStockTransferTransitBalanceError(
                                    "Серийный экземпляр уже отправлялся этим перемещением."
                                )
                            sent_serials.add(serial)
                        balance[key] = QuantityArithmeticPolicy.add(
                            available, actual.quantity
                        )
                    else:
                        if actual.quantity.value > available.value:
                            raise InvalidStockTransferTransitBalanceError(
                                "История приёмок превышает ранее отправленный состав LOT/SERIAL."
                            )
                        balance[key] = QuantityArithmeticPolicy.subtract(
                            available, actual.quantity
                        )
                if total != row.quantity:
                    raise InvalidStockTransferTransitBalanceError(
                        "Сумма фактических строк отличается от принятого результата."
                    )
                totals = sent if incoming else received
                totals[row.transfer_line_id] = QuantityArithmeticPolicy.add(
                    totals.get(row.transfer_line_id, zero), total
                )
            if assigned != set(actual_lines):
                raise InvalidStockTransferTransitBalanceError(
                    "Принятый результат должен охватывать весь транзитный факт."
                )
        if used_facts != set(facts):
            raise InvalidStockTransferTransitBalanceError(
                "Переданы лишние транзитные факты."
            )
        if any(
            sent.get(line.id, zero) != line.dispatched_qty
            or received.get(line.id, zero) != line.received_qty
            for line in transfer.lines
        ):
            raise InvalidStockTransferTransitBalanceError(
                "История не совпадает с накопленными отправками и приёмками."
            )
        result = StockTransferTransitBalanceSnapshot(
            transfer.id,
            transfer.version,
            transfer.source_warehouse_id,
            transfer.destination_warehouse_id,
            transfer.owner_id,
            transfer.transit,
            tuple(
                StockTransferTransitBalanceLineSnapshot(*key, quantity)
                for key, quantity in balance.items()
                if not quantity.value.is_zero()
            ),
            tuple(sorted(execution_ids, key=lambda value: value.uuid.int)),
            tuple(sorted(line_ids, key=lambda value: value.uuid.int)),
        )
        StockTransferTransitBalancePolicy.ensure_compatible(
            transfer=transfer, balance=result
        )
        return result

    @staticmethod
    def ensure_compatible(
        *,
        transfer: StockTransferReceiptPlanSnapshot,
        balance: StockTransferTransitBalanceSnapshot,
    ) -> None:
        """Проверяет актуальность области и равенство сумм состава текущему непринятому количеству строк."""
        if not isinstance(transfer, StockTransferReceiptPlanSnapshot) or not isinstance(
            balance, StockTransferTransitBalanceSnapshot
        ):
            raise InvalidStockTransferTransitBalanceError(
                "Нужны снимки прогресса и остатка транзита."
            )
        transfer.ensure_valid()
        balance.ensure_valid()
        if transfer.version != balance.transfer_version:
            raise StockTransferVersionConflictError(
                "Остаток транзита построен по другой версии перемещения."
            )
        if (
            balance.transfer_id != transfer.id
            or balance.source_warehouse_id != transfer.source_warehouse_id
            or balance.destination_warehouse_id != transfer.destination_warehouse_id
            or balance.owner_id != transfer.owner_id
            or balance.transit != transfer.transit
        ):
            raise InvalidStockTransferTransitBalanceError(
                "Область остатка не соответствует перемещению."
            )
        plan = {line.id: line for line in transfer.lines}
        totals = {}
        for row in balance.lines:
            line = plan.get(row.transfer_line_id)
            if (
                line is None
                or row.dimensions.inventory_item_id != line.inventory_item_id
                or row.base_uom != line.base_uom
            ):
                raise InvalidStockTransferTransitBalanceError(
                    "Состав остатка не соответствует строке плана."
                )
            totals[line.id] = QuantityArithmeticPolicy.add(
                totals.get(line.id, QuantityVO(Decimal(0))), row.quantity
            )
        if any(
            totals.get(line.id, QuantityVO(Decimal(0)))
            != QuantityArithmeticPolicy.subtract(line.dispatched_qty, line.received_qty)
            for line in transfer.lines
        ):
            raise InvalidStockTransferTransitBalanceError(
                "Суммы состава отличаются от непринятого количества строк."
            )
