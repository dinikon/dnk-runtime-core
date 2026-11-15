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
from src.modules.inventory.domain.value_object.stock_status import StockStatus
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
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
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
        """Ограничивает реализованное хранение поступлением без потери иных маршрутов."""
        if execution.operation_type is not StockOperationType.RECEIPT:
            raise NotImplementedError(
                "Хранение иных маршрутов добавляется отдельным срезом."
            )
        return dict(
            id=execution.id.uuid,
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
            if not isinstance(line.route, ReceiptExecutionRouteVO):
                raise NotImplementedError("Ожидался маршрут поступления.")
            dims = line.route.destination
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
                    lot_id=dims.lot_id.uuid if dims.lot_id else None,
                    serial_id=dims.serial_id.uuid if dims.serial_id else None,
                    stock_status=dims.stock_status.value,
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
    ) -> StockExecution:
        """Восстанавливает полный факт без текущих дат, цен и справочников."""
        return StockExecution.restore(
            identifier=StockExecutionIdVO(model.id),
            document_id=StockDocumentIdVO(model.document_id),
            document_version=model.document_version,
            operation_type=StockOperationType(model.operation_type),
            warehouse_id=WarehouseIdVO(model.warehouse_id),
            owner_id=StockOwnerIdVO(model.owner_id),
            executed_at=model.executed_at,
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
                    route=ReceiptExecutionRouteVO(
                        StockDimensionsVO(
                            InventoryItemIdVO(line.inventory_item_id),
                            StockLocationIdVO(line.location_id),
                            StockOwnerIdVO(model.owner_id),
                            StockLotIdVO(line.lot_id) if line.lot_id else None,
                            StockSerialIdVO(line.serial_id) if line.serial_id else None,
                            StockStatus(line.stock_status),
                        )
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
