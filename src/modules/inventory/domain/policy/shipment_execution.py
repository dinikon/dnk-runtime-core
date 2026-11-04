from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentExecutionBindingError,
    InvalidShipmentExecutionPlanSnapshotError,
    InvalidShipmentExecutionRegistrationSnapshotError,
    ShipmentExecutionMismatchError,
    ShipmentQuantityExceededError,
    ShipmentStatusError,
    ShipmentTimeError,
    ShipmentVersionConflictError,
)
from src.modules.inventory.domain.shipment.execution_snapshot import (
    ShipmentExecutionPlanSnapshot,
)
from src.modules.inventory.domain.shipment.registration_snapshot import (
    ShipmentExecutionRegistrationLineSnapshot,
    ShipmentExecutionRegistrationSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.execution_binding import (
    ShipmentExecutionBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionReservationSnapshotError,
)
from src.modules.inventory.domain.stock_execution.reservation_snapshot import (
    StockExecutionReservationSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)


class ShipmentExecutionPolicy:
    """Назначает фактические строки расхода плану отгрузки без изменения участвующих агрегатов."""

    @staticmethod
    def build_registration(
        *,
        shipment: ShipmentExecutionPlanSnapshot,
        execution: StockExecutionReservationSnapshot,
        bindings: tuple[ShipmentExecutionBindingVO, ...],
    ) -> ShipmentExecutionRegistrationSnapshot:
        """Суммирует количества выбранных целых строк, выводя резерв из текущего плана Shipment."""
        if not isinstance(shipment, ShipmentExecutionPlanSnapshot):
            raise InvalidShipmentExecutionPlanSnapshotError(
                "Нужен снимок текущего плана Shipment."
            )
        shipment.ensure_valid()
        if not isinstance(execution, StockExecutionReservationSnapshot):
            raise InvalidStockExecutionReservationSnapshotError(
                "Нужен снимок фактических строк исполнения."
            )
        execution.ensure_valid()
        if execution.operation_type is not StockOperationType.ISSUE:
            raise ShipmentExecutionMismatchError(
                "Отгрузка регистрируется только по ISSUE."
            )
        if not isinstance(bindings, tuple) or not bindings:
            raise InvalidShipmentExecutionBindingError(
                "Нужен непустой tuple соответствий фактических и плановых строк."
            )
        plan = {line.id: line for line in shipment.lines}
        facts = {line.id: line for line in execution.lines}
        selected = {}
        for binding in bindings:
            if not isinstance(binding, ShipmentExecutionBindingVO):
                raise InvalidShipmentExecutionBindingError(
                    "Нужны ShipmentExecutionBindingVO."
                )
            if binding.execution_line_id in selected:
                raise ShipmentExecutionMismatchError(
                    "Фактическую строку можно назначить только один раз."
                )
            if (
                binding.execution_line_id not in facts
                or binding.shipment_line_id not in plan
            ):
                raise ShipmentExecutionMismatchError(
                    "Не найдена фактическая или плановая строка назначения."
                )
            selected[binding.execution_line_id] = binding.shipment_line_id
        quantities, ids = {}, {}
        for identifier in sorted(selected, key=lambda value: value.uuid.int):
            line = facts[identifier]
            target = plan[selected[identifier]]
            if (
                line.inventory_item_id != target.inventory_item_id
                or line.base_uom != target.base_uom
            ):
                raise ShipmentExecutionMismatchError(
                    "Товар и базовая единица факта не соответствуют плану."
                )
            previous = quantities.get(target.id)
            quantities[target.id] = (
                line.quantity
                if previous is None
                else QuantityArithmeticPolicy.add(previous, line.quantity)
            )
            ids.setdefault(target.id, []).append(identifier)
        registration = ShipmentExecutionRegistrationSnapshot(
            shipment_id=shipment.id,
            shipment_version=shipment.version,
            execution_id=execution.id,
            operation_type=execution.operation_type,
            warehouse_id=execution.warehouse_id,
            owner_id=execution.owner_id,
            executed_at=execution.executed_at,
            lines=tuple(
                ShipmentExecutionRegistrationLineSnapshot(
                    shipment_line_id=identifier,
                    inventory_item_id=plan[identifier].inventory_item_id,
                    base_uom=plan[identifier].base_uom,
                    reservation_id=plan[identifier].reservation_id,
                    quantity=quantities[identifier],
                    execution_line_ids=tuple(ids[identifier]),
                )
                for identifier in sorted(quantities, key=lambda value: value.uuid.int)
            ),
        )
        ShipmentExecutionPolicy.ensure_compatible(
            shipment=shipment, registration=registration
        )
        return registration

    @staticmethod
    def ensure_compatible(
        *,
        shipment: ShipmentExecutionPlanSnapshot,
        registration: ShipmentExecutionRegistrationSnapshot,
    ) -> None:
        """Повторно проверяет статус, версию, время, неизменяемые привязки и лимит накопленного прогресса."""
        if not isinstance(shipment, ShipmentExecutionPlanSnapshot):
            raise InvalidShipmentExecutionPlanSnapshotError(
                "Нужен снимок плана отгрузки."
            )
        shipment.ensure_valid()
        if not isinstance(registration, ShipmentExecutionRegistrationSnapshot):
            raise InvalidShipmentExecutionRegistrationSnapshotError(
                "Нужен результат назначения фактических строк."
            )
        registration.ensure_valid()
        if shipment.status not in (
            ShipmentStatus.CONFIRMED,
            ShipmentStatus.PARTIALLY_SHIPPED,
        ):
            raise ShipmentStatusError(
                "Принимать факт можно только в подтверждённое или частично отгруженное отправление."
            )
        if registration.shipment_version != shipment.version:
            raise ShipmentVersionConflictError(
                "Результат построен по другой версии Shipment."
            )
        if (
            registration.shipment_id != shipment.id
            or registration.warehouse_id != shipment.warehouse_id
            or registration.owner_id != shipment.owner_id
        ):
            raise ShipmentExecutionMismatchError(
                "Отгрузка, склад и владелец должны соответствовать плану."
            )
        if registration.executed_at < shipment.updated_at:
            raise ShipmentTimeError(
                "Факт не может предшествовать состоянию плана, по которому он принимается."
            )
        by_line = {line.id: line for line in shipment.lines}
        for line in registration.lines:
            target = by_line.get(line.shipment_line_id)
            if (
                target is None
                or target.inventory_item_id != line.inventory_item_id
                or target.base_uom != line.base_uom
                or target.reservation_id != line.reservation_id
            ):
                raise ShipmentExecutionMismatchError(
                    "Строка, товар, единица и резерв не соответствуют плану Shipment."
                )
            total = QuantityArithmeticPolicy.add(target.shipped_qty, line.quantity)
            if total.value > target.planned_qty.value:
                raise ShipmentQuantityExceededError(
                    "Фактическое количество превышает оставшийся план строки."
                )
