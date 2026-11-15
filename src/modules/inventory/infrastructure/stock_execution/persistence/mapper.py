from src.modules.inventory.domain.stock_execution.value_object.return_receipt_route import (
    ReturnReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.return_issue_route import (
    ReturnIssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_document.value_object.return_details import (
    StockReturnDetailsVO,
)
from src.modules.inventory.domain.stock_document.value_object.return_reason import (
    ReturnReasonVO,
)
from src.modules.inventory.domain.stock_document.value_object.return_direction import (
    ReturnDirection,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_return import (
    StockExecutionReturnModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_return_line import (
    StockExecutionReturnLineModel,
)
from dataclasses import replace
from src.modules.inventory.domain.stock_execution.value_object.status_change_route import (
    StatusChangeExecutionRouteVO,
)
from src.modules.inventory.domain.stock_document.value_object.status_change_details import (
    StockStatusChangeDetailsVO,
)
from src.modules.inventory.domain.stock_document.value_object.status_change_reason import (
    StatusChangeReasonVO,
)
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.infrastructure.persistence.models.stock_execution_status_change import (
    StockExecutionStatusChangeModel,
)
from src.modules.inventory.domain.stock_execution.value_object.write_off_route import (
    WriteOffExecutionRouteVO,
)
from src.modules.inventory.domain.stock_document.value_object.write_off_reason import (
    WriteOffReasonVO,
)
from src.modules.inventory.domain.stock_execution.value_object.internal_move_route import (
    InternalMoveExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_cost_evidence_id import (
    ReceiptCostEvidenceIdVO,
)
from typing import Any
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from collections.abc import Sequence
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.entity.receipt_cost_evidence import (
    ReceiptCostEvidence,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_cost_allocation import (
    ReceiptCostAllocationVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_cost_evidence import (
    ReceiptCostEvidenceModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_cost_allocations import (
    ReceiptCostAllocationModel,
)


class StockExecutionMapper:
    """Хранит фактические строки и собственные неизменяемые стоимостные основания."""

    @staticmethod
    def to_values(execution: StockExecution) -> dict[str, Any]:
        """Хранит RECEIPT, ISSUE и INTERNAL_MOVE без потери сторон маршрута."""
        if execution.operation_type not in (
            StockOperationType.RECEIPT,
            StockOperationType.ISSUE,
            StockOperationType.WRITE_OFF,
            StockOperationType.STATUS_CHANGE,
            StockOperationType.RETURN,
            StockOperationType.INTERNAL_MOVE,
        ):
            raise NotImplementedError(
                "Хранение иных маршрутов добавляется отдельным срезом."
            )
        return dict(
            id=execution.id.uuid,
            write_off_reason=(
                execution.write_off_reason.value if execution.write_off_reason else None
            ),
            document_id=execution.document_id.uuid,
            document_version=execution.document_version,
            operation_type=execution.operation_type.value,
            warehouse_id=execution.warehouse_id.uuid,
            owner_id=execution.owner_id.uuid,
            executed_at=execution.executed_at,
        )

    @staticmethod
    def line_values(execution: StockExecution) -> list[dict[str, Any]]:
        """Сохраняет порядок, исходный пересчёт и фактические измерения без новых ID."""
        values = []
        for position, line in enumerate(execution.lines):
            if isinstance(
                line.route, (ReceiptExecutionRouteVO, ReturnReceiptExecutionRouteVO)
            ):
                dims = line.route.destination
            elif isinstance(
                line.route,
                (
                    IssueExecutionRouteVO,
                    WriteOffExecutionRouteVO,
                    ReturnIssueExecutionRouteVO,
                ),
            ):
                dims = line.route.source
            elif isinstance(
                line.route, (InternalMoveExecutionRouteVO, StatusChangeExecutionRouteVO)
            ):
                dims = line.route.source
            else:
                raise NotImplementedError("Хранение маршрута не реализовано.")
            values.append(
                dict(
                    id=line.id.uuid,
                    execution_id=execution.id.uuid,
                    position=position,
                    document_line_id=line.document_line_id.uuid,
                    inventory_item_id=line.inventory_item_id.uuid,
                    base_uom=line.base_uom.value,
                    quantity=line.quantity.value,
                    source_quantity=line.conversion.quantity.value,
                    source_uom=line.conversion.uom.value,
                    factor_to_base=line.conversion.factor_to_base,
                    location_id=dims.location_id.uuid,
                    destination_location_id=(
                        line.route.destination.location_id.uuid
                        if isinstance(line.route, InternalMoveExecutionRouteVO)
                        else None
                    ),
                    lot_id=dims.lot_id.uuid if dims.lot_id else None,
                    serial_id=dims.serial_id.uuid if dims.serial_id else None,
                    stock_status=dims.stock_status.value,
                    destination_stock_status=(
                        line.route.destination.stock_status.value
                        if isinstance(line.route, StatusChangeExecutionRouteVO)
                        else None
                    ),
                )
            )
        return values

    @staticmethod
    def cost_values(execution: StockExecution) -> list[dict[str, Any]]:
        """Сохраняет именно известные суммы, не создавая основание для неизвестной стоимости."""
        return [
            dict(
                id=c.id.uuid,
                execution_id=execution.id.uuid,
                total_amount=c.total.amount,
                currency=c.total.currency.value,
                basis_kind=c.basis_kind,
                source_system=c.source_system,
                source_reference=c.source_reference,
            )
            for c in execution.receipt_cost_evidence
        ]

    @staticmethod
    def allocation_values(execution: StockExecution) -> list[dict[str, Any]]:
        """Привязывает суммы к собственным фактическим строкам."""
        return [
            dict(
                evidence_id=c.id.uuid,
                execution_line_id=a.execution_line_id.uuid,
                amount=a.amount.amount,
            )
            for c in execution.receipt_cost_evidence
            for a in c.allocations
        ]

    @staticmethod
    def to_domain(
        model: StockExecutionModel,
        lines: Sequence[StockExecutionLineModel],
        costs: Sequence[ReceiptCostEvidenceModel],
        allocations: Sequence[ReceiptCostAllocationModel],
        status_change: StockExecutionStatusChangeModel | None = None,
        return_details: StockExecutionReturnModel | None = None,
        return_lines: Sequence[StockExecutionReturnLineModel] = (),
    ) -> StockExecution:
        """Восстанавливает полный факт без текущих дат, цен и справочников."""
        if model.operation_type not in (
            "RECEIPT",
            "ISSUE",
            "INTERNAL_MOVE",
            "WRITE_OFF",
            "STATUS_CHANGE",
            "RETURN",
        ):
            raise NotImplementedError(
                "Восстановление маршрута исполнения не реализовано."
            )
        return StockExecution.restore(
            identifier=StockExecutionIdVO(model.id),
            document_id=StockDocumentIdVO(model.document_id),
            document_version=model.document_version,
            operation_type=StockOperationType(model.operation_type),
            return_details=(
                StockReturnDetailsVO(
                    StockExecutionIdVO(return_details.origin_execution_id),
                    ReturnDirection(return_details.direction),
                    ReturnReasonVO(return_details.reason),
                )
                if return_details is not None
                else None
            ),
            status_change_details=(
                StockStatusChangeDetailsVO(
                    StockStatus(status_change.target_status),
                    StatusChangeReasonVO(status_change.reason),
                )
                if status_change is not None
                else None
            ),
            warehouse_id=WarehouseIdVO(model.warehouse_id),
            owner_id=StockOwnerIdVO(model.owner_id),
            executed_at=model.executed_at,
            write_off_reason=(
                WriteOffReasonVO(model.write_off_reason)
                if model.write_off_reason is not None
                else None
            ),
            lines=tuple(
                StockExecutionLine.restore(
                    identifier=StockExecutionLineIdVO(line.id),
                    document_line_id=StockDocumentLineIdVO(line.document_line_id),
                    inventory_item_id=InventoryItemIdVO(line.inventory_item_id),
                    base_uom=UomCodeVO(line.base_uom),
                    quantity=QuantityVO(line.quantity),
                    conversion=QuantityConversionSnapshotVO(
                        QuantityVO(line.source_quantity),
                        UomCodeVO(line.source_uom),
                        line.factor_to_base,
                    ),
                    route=StockExecutionMapper._route(
                        model,
                        line,
                        return_details,
                        next(
                            (
                                link
                                for link in return_lines
                                if link.execution_line_id == line.id
                            ),
                            None,
                        ),
                    ),
                )
                for line in lines
            ),
            receipt_cost_evidence=tuple(
                ReceiptCostEvidence.restore(
                    identifier=ReceiptCostEvidenceIdVO(c.id),
                    total=MoneyVO(c.total_amount, CurrencyVO(c.currency)),
                    basis_kind=c.basis_kind,
                    source_system=c.source_system,
                    source_reference=c.source_reference,
                    allocations=tuple(
                        ReceiptCostAllocationVO(
                            StockExecutionLineIdVO(a.execution_line_id),
                            MoneyVO(a.amount, CurrencyVO(c.currency)),
                        )
                        for a in allocations
                        if a.evidence_id == c.id
                    ),
                )
                for c in costs
            ),
        )

    @staticmethod
    def _route(
        model: StockExecutionModel,
        line: StockExecutionLineModel,
        return_details: StockExecutionReturnModel | None = None,
        return_line: StockExecutionReturnLineModel | None = None,
    ) -> (
        ReceiptExecutionRouteVO
        | IssueExecutionRouteVO
        | WriteOffExecutionRouteVO
        | InternalMoveExecutionRouteVO
        | StatusChangeExecutionRouteVO
        | ReturnReceiptExecutionRouteVO
        | ReturnIssueExecutionRouteVO
    ):
        """Восстанавливает сохранённый тип маршрута без текущего физического контекста."""
        source = StockDimensionsVO(
            InventoryItemIdVO(line.inventory_item_id),
            StockLocationIdVO(line.location_id),
            StockOwnerIdVO(model.owner_id),
            StockLotIdVO(line.lot_id) if line.lot_id else None,
            StockSerialIdVO(line.serial_id) if line.serial_id else None,
            StockStatus(line.stock_status),
        )
        if model.operation_type == "RETURN":
            if return_details is None or return_line is None:
                raise RuntimeError("Возврат не содержит собственного основания.")
            return (
                ReturnReceiptExecutionRouteVO(
                    StockExecutionLineIdVO(return_line.origin_execution_line_id), source
                )
                if ReturnDirection(return_details.direction)
                is ReturnDirection.FROM_RECIPIENT
                else ReturnIssueExecutionRouteVO(
                    StockExecutionLineIdVO(return_line.origin_execution_line_id), source
                )
            )
        if model.operation_type == "STATUS_CHANGE":
            if (
                line.destination_stock_status is None
                or line.destination_location_id is None
            ):
                raise RuntimeError("Сохранённый маршрут не содержит нового состояния.")
            return StatusChangeExecutionRouteVO(
                source,
                replace(
                    source,
                    location_id=StockLocationIdVO(line.destination_location_id),
                    stock_status=StockStatus(line.destination_stock_status),
                ),
            )
        if model.operation_type == "WRITE_OFF":
            return WriteOffExecutionRouteVO(source)
        if model.operation_type == "INTERNAL_MOVE":
            if line.destination_location_id is None:
                raise RuntimeError(
                    "Сохранённый маршрут перемещения не содержит назначения."
                )
            return InternalMoveExecutionRouteVO.to_location(
                source, StockLocationIdVO(line.destination_location_id)
            )
        return (
            ReceiptExecutionRouteVO(source)
            if model.operation_type == "RECEIPT"
            else IssueExecutionRouteVO(source)
        )

    @staticmethod
    def status_change_values(execution: StockExecution) -> dict[str, object]:
        """Извлекает собственные параметры операции без SQL и генерации идентичности."""
        details = execution.status_change_details
        if details is None:
            raise RuntimeError("Агрегат не содержит параметров изменения состояния.")
        return {
            "execution_id": execution.id.uuid,
            "target_status": details.target_status.value,
            "reason": details.reason.value,
        }

    @staticmethod
    def return_values(value: StockExecution) -> dict[str, object]:
        """Извлекает собственные реквизиты возврата для неизменяемой записи или сохранения плана."""
        details = value.return_details
        if details is None:
            raise RuntimeError("Нет реквизитов возврата.")
        return {
            "execution_id": value.id.uuid,
            "origin_execution_id": details.origin_execution_id.uuid,
            "direction": details.direction.value,
            "reason": details.reason.value,
        }

    @staticmethod
    def return_line_values(value: StockExecution) -> list[dict[str, object]]:
        """Извлекает собственные дочерние связи без генерации ID или бизнес-решений."""
        return [
            {
                "execution_line_id": line.id.uuid,
                "origin_execution_line_id": line.route.origin_line_id.uuid,
            }
            for line in value.lines
            if isinstance(
                line.route, (ReturnReceiptExecutionRouteVO, ReturnIssueExecutionRouteVO)
            )
        ]
