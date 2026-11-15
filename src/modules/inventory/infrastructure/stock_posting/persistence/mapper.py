from uuid import UUID
from decimal import Decimal
from typing import Any
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
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
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.posting_source import (
    PostingSourceVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.infrastructure.persistence.models.stock_postings import (
    StockPostingModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_ledger_entries import (
    StockLedgerEntryModel,
)


class StockPostingMapper:
    """Преобразует проведение и принадлежащий ему исторический Ledger."""

    @staticmethod
    def to_values(posting: StockPosting) -> dict[str, Any]:
        """Извлекает реквизиты без изменения основания."""
        return dict(
            id=posting.id.uuid,
            execution_id=posting.source.execution_id.uuid,
            operation_type=posting.operation_type.value,
            posted_at=posting.posted_at,
            reversal_of_id=(
                posting.reversal_of_id.uuid if posting.reversal_of_id else None
            ),
        )

    @staticmethod
    def entry_values(posting: StockPosting) -> list[dict[str, Any]]:
        """Сохраняет точные дельты, исходный пересчёт и порядок записей."""
        return [
            dict(
                id=e.id.uuid,
                posting_id=posting.id.uuid,
                position=index,
                position_id=e.position_id.uuid,
                quantity_delta=e.quantity_delta.value,
                base_uom=e.base_uom.value,
                source_quantity=e.conversion.quantity.value,
                source_uom=e.conversion.uom.value,
                factor_to_base=e.conversion.factor_to_base,
            )
            for index, e in enumerate(posting.entries)
        ]

    @staticmethod
    def to_domain(
        model: StockPostingModel, entries: Sequence[StockLedgerEntryModel]
    ) -> StockPosting:
        """Восстанавливает полный факт без повторного проведения и текущих коэффициентов."""
        return StockPosting.restore(
            identifier=StockPostingIdVO(model.id),
            source=PostingSourceVO(StockExecutionIdVO(model.execution_id)),
            operation_type=StockOperationType(model.operation_type),
            posted_at=model.posted_at,
            reversal_of_id=(
                StockPostingIdVO(model.reversal_of_id) if model.reversal_of_id else None
            ),
            entries=tuple(
                StockLedgerEntry.restore(
                    identifier=StockLedgerEntryIdVO(e.id),
                    position_id=StockPositionIdVO(e.position_id),
                    quantity_delta=StockDeltaVO(e.quantity_delta),
                    base_uom=UomCodeVO(e.base_uom),
                    conversion=QuantityConversionSnapshotVO(
                        QuantityVO(e.source_quantity),
                        UomCodeVO(e.source_uom),
                        e.factor_to_base,
                    ),
                )
                for e in entries
            ),
        )
