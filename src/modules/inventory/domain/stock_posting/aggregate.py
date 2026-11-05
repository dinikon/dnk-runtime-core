from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.inventory_count.adjustment_source_snapshot import (
    InventoryCountAdjustmentSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.result_snapshot import (
    InventoryCountResultSnapshot,
)
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.policy.stock_adjustment_execution import (
    StockAdjustmentExecutionPolicy,
)
from src.modules.inventory.domain.policy.stock_adjustment_posting import (
    StockAdjustmentPostingPolicy,
)
from src.modules.inventory.domain.stock_document.adjustment_execution_snapshot import (
    StockDocumentAdjustmentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_execution.adjustment_snapshot import (
    StockAdjustmentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_posting.adjustment_entry_snapshot import (
    StockAdjustmentEntrySnapshot,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot

from src.modules.inventory.domain.policy.stock_execution_posting import (
    StockExecutionPostingPolicy,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionPostingSnapshotError,
)
from src.modules.inventory.domain.stock_execution.posting_snapshot import (
    StockExecutionPostingSnapshot,
)
from src.modules.inventory.domain.policy.stock_movement_balance import (
    StockMovementBalancePolicy,
)
from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidPostingContextError,
    InvalidStockPostingSnapshotError,
    InvalidStockReversalError,
    StockPostingExecutionTimeError,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_posting.value_object.posting_source import (
    PostingSourceVO,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


@dataclass(frozen=True, slots=True)
class StockPosting:
    """Неизменяемый факт проведения, владеющий журналом без прямого изменения позиций."""

    id: StockPostingIdVO
    source: PostingSourceVO
    operation_type: StockOperationType
    posted_at: datetime
    entries: tuple[StockLedgerEntry, ...]
    reversal_of_id: StockPostingIdVO | None

    @classmethod
    def create(
        cls,
        *,
        identifier: StockPostingIdVO,
        source: PostingSourceVO,
        operation_type: StockOperationType,
        posted_at: datetime,
        entries: tuple[StockLedgerEntry, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...] = (),
    ) -> Self:
        """Создаёт завершённое обычное проведение по снимкам позиций и системному пересчёту."""
        if operation_type is StockOperationType.ADJUSTMENT:
            raise StockAdjustmentError(
                "Корректировка проводится только из полного факта с повторной проверкой основания."
            )
        posting = cls.restore(
            identifier=identifier,
            source=source,
            operation_type=operation_type,
            posted_at=posted_at,
            entries=entries,
            reversal_of_id=None,
        )
        for entry in posting.entries:
            entry.ensure_current_conversion()
        posting._ensure_context(positions=positions, locations=locations)
        return posting

    @classmethod
    def create_from_execution(
        cls,
        *,
        identifier: StockPostingIdVO,
        execution: StockExecutionPostingSnapshot,
        posted_at: datetime,
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        entry_bindings: tuple[StockPostingEntryBindingVO, ...],
    ) -> Self:
        """Выводит основание и записи из исполнения, сохраняя один однонаправленный итог на позицию."""
        if not isinstance(execution, StockExecutionPostingSnapshot):
            raise InvalidStockExecutionPostingSnapshotError(
                "Нужен снимок исполнения для построения журнала."
            )
        execution.ensure_valid()
        normalized = StockPostingPolicy.normalize_time(posted_at)
        if normalized < execution.executed_at:
            raise StockPostingExecutionTimeError(
                "Проведение не может быть раньше фактического исполнения."
            )
        entries = StockExecutionPostingPolicy.build_entries(
            execution=execution,
            positions=positions,
            locations=locations,
            entry_bindings=entry_bindings,
        )
        return cls.create(
            identifier=identifier,
            source=PostingSourceVO(execution.id),
            operation_type=execution.operation_type,
            posted_at=normalized,
            entries=entries,
            positions=positions,
            locations=(
                locations
                if execution.operation_type is StockOperationType.INTERNAL_MOVE
                else ()
            ),
        )

    @classmethod
    def create_from_adjustment_execution(
        cls,
        *,
        identifier: StockPostingIdVO,
        execution: StockAdjustmentExecutionSnapshot,
        document: StockDocumentAdjustmentExecutionSnapshot,
        posted_at: datetime,
        inventory_count: InventoryCountAdjustmentSourceSnapshot,
        result: InventoryCountResultSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        found_positions: tuple[StockPositionCountingSnapshot, ...],
        entry_bindings: tuple[StockPostingEntryBindingVO, ...],
        presence: tuple[StockSerialPresenceSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> Self:
        """Строит полный Ledger корректировки по заново проверенному исходному запасу и новым нулевым FOUND-позициям."""
        normalized = StockPostingPolicy.normalize_time(posted_at)
        StockAdjustmentExecutionPolicy.ensure_current(
            execution=execution,
            document=document,
            inventory_count=inventory_count,
            result=result,
            baseline=baseline,
            warehouse=warehouse,
            inventory_items=inventory_items,
            locations=locations,
            positions=positions,
            as_of=normalized,
            presence=presence,
            lots=lots,
            serials=serials,
        )
        entries = StockAdjustmentPostingPolicy.build_entries(
            execution=execution,
            positions=positions,
            found_positions=found_positions,
            entry_bindings=entry_bindings,
        )
        return cls.restore(
            identifier=identifier,
            source=PostingSourceVO(execution.id),
            operation_type=StockOperationType.ADJUSTMENT,
            posted_at=normalized,
            entries=entries,
            reversal_of_id=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockPostingIdVO,
        source: PostingSourceVO,
        operation_type: StockOperationType,
        posted_at: datetime,
        entries: tuple[StockLedgerEntry, ...],
        reversal_of_id: StockPostingIdVO | None,
    ) -> Self:
        """Восстанавливает полный исторический состав без текущих снимков и новых коэффициентов."""
        posting = cls(
            identifier,
            source,
            operation_type,
            StockPostingPolicy.normalize_time(posted_at),
            entries,
            reversal_of_id,
        )
        posting._validate()
        return posting

    @classmethod
    def create_reversal(
        cls,
        *,
        identifier: StockPostingIdVO,
        source: PostingSourceVO,
        posted_at: datetime,
        original: StockPostingSnapshot,
        entry_ids: tuple[StockLedgerEntryIdVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...] = (),
    ) -> Self:
        """Создаёт точную компенсацию всех записей с новыми ID и основанием без правки оригинала."""
        if not isinstance(original, StockPostingSnapshot):
            raise InvalidStockPostingSnapshotError("Нужен снимок исходного проведения.")
        original.ensure_valid()
        if original.operation_type is StockOperationType.ADJUSTMENT:
            raise StockAdjustmentError(
                "Сторно корректировки требует отдельного сценария с новым основанием."
            )
        normalized = StockPostingPolicy.normalize_time(posted_at)
        if (
            not isinstance(identifier, StockPostingIdVO)
            or identifier == original.id
            or not isinstance(source, PostingSourceVO)
            or source.execution_id == original.source.execution_id
            or normalized < original.posted_at
            or not isinstance(entry_ids, tuple)
            or len(entry_ids) != len(original.entries)
        ):
            raise InvalidStockReversalError(
                "Компенсация требует новых ID и основания, полного состава и времени не раньше исходного."
            )
        original_ids = {entry.id for entry in original.entries}
        entries = []
        for entry_id, entry in zip(entry_ids, original.entries, strict=True):
            if (
                not isinstance(entry_id, StockLedgerEntryIdVO)
                or entry_id in original_ids
            ):
                raise InvalidStockReversalError(
                    "Каждая компенсирующая запись требует нового StockLedgerEntryIdVO."
                )
            entries.append(
                StockLedgerEntry.restore(
                    identifier=entry_id,
                    position_id=entry.position_id,
                    quantity_delta=StockDeltaVO(
                        entry.quantity_delta.value.copy_negate()
                    ),
                    base_uom=entry.base_uom,
                    conversion=entry.conversion,
                )
            )
        posting = cls.restore(
            identifier=identifier,
            source=source,
            operation_type=original.operation_type,
            posted_at=normalized,
            entries=tuple(entries),
            reversal_of_id=original.id,
        )
        posting._ensure_context(positions=positions, locations=locations)
        return posting

    def adjustment_entries(
        self, execution: StockAdjustmentExecutionSnapshot
    ) -> tuple[StockAdjustmentEntrySnapshot, ...]:
        """Выдаёт адресные снимки для физических позиций после полного сопоставления Ledger с фактом."""
        return StockAdjustmentPostingPolicy.application_snapshots(
            posting=self.snapshot(), execution=execution
        )

    def snapshot(self) -> StockPostingSnapshot:
        """Возвращает проверенный состав для будущей компенсации без чужих агрегатов."""
        self._validate()
        return StockPostingSnapshot(
            self.id,
            self.source,
            self.operation_type,
            self.posted_at,
            self.entries,
            self.reversal_of_id,
        )

    def _validate(self) -> None:
        """Проверяет собственный состав и обычные знаки без текущих настроек и I/O."""
        StockPostingPolicy.ensure_valid(
            identifier=self.id,
            source=self.source,
            operation_type=self.operation_type,
            posted_at=self.posted_at,
            entries=self.entries,
            reversal_of_id=self.reversal_of_id,
        )

    def _ensure_context(
        self,
        *,
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
    ) -> None:
        """Сверяет ссылки и баланс перемещения, оставляя доступность и физический переход позициям."""
        if self.operation_type is StockOperationType.INTERNAL_MOVE:
            StockMovementBalancePolicy.ensure_balanced(
                entries=self.entries, positions=positions, locations=locations
            )
        else:
            if not isinstance(locations, tuple) or locations:
                raise InvalidPostingContextError(
                    "Локации отдельно передаются только для внутреннего перемещения."
                )
            StockPostingPolicy.ensure_positions(
                entries=self.entries, positions=positions
            )
