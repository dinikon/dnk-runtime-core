import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from src.modules.inventory.application.stock_document.command.create_receipt_draft.dto import (
    CreateReceiptDraftResultDTO,
    CreateReceiptDraftLineDTO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)


class ReceiptCreationResultMapper:
    """Сохраняет исходный результат сценария независимо от будущих изменений справочников."""

    @staticmethod
    def to_record(result: CreateReceiptDraftResultDTO) -> dict[str, Any]:
        """Кодирует Decimal строками без округления и без HTTP-зависимости."""
        return json.loads(json.dumps(asdict(result), default=str))

    @staticmethod
    def from_record(record: dict[str, Any]) -> CreateReceiptDraftResultDTO:
        """Восстанавливает конкретный DTO из доверенной записи идемпотентности."""
        return CreateReceiptDraftResultDTO(
            id=UUID(record["id"]),
            operation_type=StockOperationType(record["operation_type"]),
            status=StockDocumentStatus(record["status"]),
            warehouse_id=UUID(record["warehouse_id"]),
            warehouse_code=record["warehouse_code"],
            warehouse_name=record["warehouse_name"],
            owner_id=UUID(record["owner_id"]),
            owner_name=record["owner_name"],
            source_system=record["source_system"],
            source_reference=record["source_reference"],
            source_version=record["source_version"],
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
            version=record["version"],
            lines=tuple(
                CreateReceiptDraftLineDTO(
                    id=UUID(line["id"]),
                    position=line["position"],
                    inventory_item_id=UUID(line["inventory_item_id"]),
                    sku=line["sku"],
                    base_uom=line["base_uom"],
                    planned_qty=Decimal(line["planned_qty"]),
                    source_quantity=Decimal(line["source_quantity"]),
                    source_uom=line["source_uom"],
                    factor_to_base=Decimal(line["factor_to_base"]),
                    executed_qty=Decimal(line["executed_qty"]),
                )
                for line in record["lines"]
            ),
        )
