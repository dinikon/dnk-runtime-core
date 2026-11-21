from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.stock_execution_document import (
    StockExecutionDocumentPolicy,
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
    InvalidStockExecutionShipmentSnapshotError,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentShipmentSnapshotError,
    InvalidStockDocumentContextError,
)
from src.modules.inventory.domain.stock_document.execution_snapshot import (
    StockDocumentExecutionSnapshot,
    StockDocumentLineExecutionSnapshot,
)
from src.modules.inventory.domain.stock_document.shipment_snapshot import (
    StockDocumentShipmentSnapshot,
)
from src.modules.inventory.domain.stock_execution.document_snapshot import (
    StockExecutionDocumentSnapshot,
)
from src.modules.inventory.domain.stock_execution.shipment_snapshot import (
    StockExecutionShipmentSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.document_line_quantity import (
    ExecutedDocumentLineQuantityVO,
)
from src.modules.inventory.domain.stock_execution.reservation_snapshot import (
    StockExecutionReservationSnapshot,
    StockExecutionReservationLineSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)


class ShipmentExecutionPolicy:
    """Назначает фактические строки расхода плану отгрузки без изменения участвующих агрегатов."""

    @staticmethod
    def build_registration_from_document(
        *,
        shipment: ShipmentExecutionPlanSnapshot,
        document: StockDocumentShipmentSnapshot,
        execution: StockExecutionShipmentSnapshot,
    ) -> ShipmentExecutionRegistrationSnapshot:
        """Выводит назначения всех фактических строк из сохранённых оснований документа, проверяя оба уровня лимитов."""
        if not isinstance(shipment, ShipmentExecutionPlanSnapshot):
            raise InvalidShipmentExecutionPlanSnapshotError(
                "Нужен текущий снимок плана Shipment."
            )
        shipment.ensure_valid()
        if not isinstance(document, StockDocumentShipmentSnapshot):
            raise InvalidStockDocumentShipmentSnapshotError(
                "Нужен снимок происхождения и прогресса документа Shipment."
            )
        document.ensure_valid()
        if not isinstance(execution, StockExecutionShipmentSnapshot):
            raise InvalidStockExecutionShipmentSnapshotError(
                "Нужен снимок факта с ID/версией документа и связями строк."
            )
        execution.ensure_valid()
        if execution.operation_type is not StockOperationType.ISSUE:
            raise ShipmentExecutionMismatchError(
                "Автоматическое назначение отгрузке доступно только для ISSUE."
            )
        if document.shipment_id != shipment.id:
            raise ShipmentExecutionMismatchError(
                "Документ относится к другому Shipment."
            )
        if document.source_shipment_version > shipment.version:
            raise ShipmentVersionConflictError(
                "Историческая версия основания документа не может превышать текущую версию Shipment."
            )
        shipment_lines = {line.id: line for line in shipment.lines}
        for line in document.lines:
            target = shipment_lines.get(line.shipment_line_id)
            if (
                target is None
                or target.inventory_item_id != line.inventory_item_id
                or target.base_uom != line.base_uom
            ):
                raise ShipmentExecutionMismatchError(
                    "Каждая строка документа должна относиться к строке, товару и единице текущего Shipment."
                )
        by_line = {line.document_line_id: line for line in document.lines}
        quantities, bindings = {}, []
        for actual in sorted(
            execution.lines, key=lambda value: value.execution_line_id.uuid.int
        ):
            planned = by_line.get(actual.document_line_id)
            if (
                planned is None
                or actual.inventory_item_id != planned.inventory_item_id
                or actual.base_uom != planned.base_uom
            ):
                raise InvalidStockDocumentContextError(
                    "Каждая фактическая строка должна соответствовать строке документа, товару и единице."
                )
            previous = quantities.get(actual.document_line_id)
            quantities[actual.document_line_id] = (
                actual.quantity
                if previous is None
                else QuantityArithmeticPolicy.add(previous, actual.quantity)
            )
            bindings.append(
                ShipmentExecutionBindingVO(
                    actual.execution_line_id, planned.shipment_line_id
                )
            )
        StockExecutionDocumentPolicy.ensure_compatible(
            document=StockDocumentExecutionSnapshot(
                document.id,
                document.operation_type,
                document.warehouse_id,
                document.owner_id,
                document.status,
                document.version,
                document.updated_at,
                tuple(
                    StockDocumentLineExecutionSnapshot(
                        line.document_line_id,
                        line.inventory_item_id,
                        line.base_uom,
                        line.planned_qty,
                        line.executed_qty,
                    )
                    for line in document.lines
                ),
            ),
            execution=StockExecutionDocumentSnapshot(
                execution.id,
                execution.document_id,
                execution.document_version,
                execution.operation_type,
                execution.warehouse_id,
                execution.owner_id,
                execution.executed_at,
                tuple(
                    ExecutedDocumentLineQuantityVO(
                        identifier,
                        by_line[identifier].inventory_item_id,
                        by_line[identifier].base_uom,
                        quantities[identifier],
                    )
                    for identifier in sorted(
                        quantities, key=lambda value: value.uuid.int
                    )
                ),
            ),
        )
        return ShipmentExecutionPolicy.build_registration(
            shipment=shipment,
            execution=StockExecutionReservationSnapshot(
                execution.id,
                execution.operation_type,
                execution.warehouse_id,
                execution.owner_id,
                execution.executed_at,
                tuple(
                    StockExecutionReservationLineSnapshot(
                        line.execution_line_id,
                        line.inventory_item_id,
                        line.base_uom,
                        line.quantity,
                    )
                    for line in execution.lines
                ),
            ),
            bindings=tuple(bindings),
        )

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
