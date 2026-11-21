from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Self

from src.modules.inventory.domain.inventory_count.value_object.completion import (
    InventoryCountCompletionVO,
)
from src.modules.inventory.domain.policy.inventory_count_completion import (
    InventoryCountCompletionPolicy,
)
from src.modules.inventory.domain.stock_document.adjustment_completion_snapshot import (
    StockDocumentAdjustmentCompletionSnapshot,
)
from src.modules.inventory.domain.stock_execution.adjustment_snapshot import (
    StockAdjustmentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_posting.adjustment_application_snapshot import (
    StockAdjustmentApplicationSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot

from src.modules.inventory.domain.inventory_count.adjustment_source_snapshot import (
    InventoryCountAdjustmentSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.result_snapshot import (
    InventoryCountResultSnapshot,
)
from src.modules.inventory.domain.inventory_count.value_object.result_ref import (
    InventoryCountResultRefVO,
)
from src.modules.inventory.domain.policy.inventory_count_result import (
    InventoryCountResultPolicy,
)
from src.modules.inventory.domain.count_sheet.reconciliation_snapshot import (
    CountSheetReconciliationSnapshot,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.inventory_count.sheet_source_snapshot import (
    InventoryCountSheetSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.start_plan_snapshot import (
    InventoryCountStartPlanSnapshot,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
)
from src.modules.inventory.domain.policy.inventory_count_start import (
    InventoryCountStartPolicy,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountValueError,
    InventoryCountStatusError,
    InventoryCountTimeError,
    InventoryCountVersionConflictError,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.policy.inventory_count_confirmation import (
    InventoryCountConfirmationPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class InventoryCount:
    """План, пересчёт и завершение по историческим фактам без коллекции ведомостей, проведения или блокировки движений."""

    id: InventoryCountIdVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    scope: CountScopeVO
    status: InventoryCountStatus
    baseline: InventoryCountBaselineRefVO | None
    result: InventoryCountResultRefVO | None
    completion: InventoryCountCompletionVO | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: InventoryCountIdVO,
        warehouse: WarehouseSnapshot,
        owner_id: StockOwnerIdVO,
        scope: CountScopeVO,
        created_at: datetime,
    ) -> Self:
        """Создаёт черновик версии 0 для активного склада без проверки адресов до подтверждения."""
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок склада инвентаризации.")
        InventoryCountConfirmationPolicy.ensure_warehouse(
            warehouse_id=warehouse.id, warehouse=warehouse
        )
        return cls.restore(
            identifier=identifier,
            warehouse_id=warehouse.id,
            owner_id=owner_id,
            scope=scope,
            status=InventoryCountStatus.DRAFT,
            baseline=None,
            result=None,
            completion=None,
            created_at=created_at,
            updated_at=created_at,
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: InventoryCountIdVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        scope: CountScopeVO,
        status: InventoryCountStatus,
        baseline: InventoryCountBaselineRefVO | None,
        result: InventoryCountResultRefVO | None,
        completion: InventoryCountCompletionVO | None,
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        """Восстанавливает собственное состояние и UTC-хронологию без актуальных внешних снимков."""
        count = cls(
            identifier,
            warehouse_id,
            owner_id,
            scope,
            status,
            baseline,
            result,
            completion,
            normalize_inventory_count_time(created_at),
            normalize_inventory_count_time(updated_at),
            version,
        )
        count._validate()
        return count

    def change_scope(
        self, scope: CountScopeVO, *, expected_version: int, updated_at: datetime
    ) -> Self:
        """Меняет область черновика; равное значение после проверок сохраняет исходный объект."""
        normalized = self._prepare_transition(expected_version, updated_at)
        if not isinstance(scope, CountScopeVO):
            raise InvalidInventoryCountValueError("Нужна область CountScopeVO.")
        scope.ensure_valid()
        if scope == self.scope:
            return self
        return self._changed(scope=scope, updated_at=normalized)

    def confirm(
        self,
        *,
        expected_version: int,
        warehouse: WarehouseSnapshot,
        locations: tuple[StockLocationSnapshot, ...] = (),
        updated_at: datetime,
    ) -> Self:
        """Фиксирует область после повторной внешней проверки без начала пересчёта."""
        normalized = self._prepare_transition(expected_version, updated_at)
        InventoryCountConfirmationPolicy.ensure_confirmable(
            warehouse_id=self.warehouse_id,
            scope=self.scope,
            warehouse=warehouse,
            locations=locations,
        )
        return self._changed(
            status=InventoryCountStatus.CONFIRMED, updated_at=normalized
        )

    def cancel(self, *, expected_version: int, updated_at: datetime) -> Self:
        """Отменяет только черновик с сохранением области без обращения к складу или остаткам."""
        normalized = self._prepare_transition(expected_version, updated_at)
        return self._changed(
            status=InventoryCountStatus.CANCELLED, updated_at=normalized
        )

    def start_plan_snapshot(self) -> InventoryCountStartPlanSnapshot:
        """Передаёт проверенный текущий план для построения независимого учётного основания."""
        self._validate()
        return InventoryCountStartPlanSnapshot(
            self.id,
            self.warehouse_id,
            self.owner_id,
            self.scope,
            self.status,
            self.updated_at,
            self.version,
        )

    def sheet_source_snapshot(self) -> InventoryCountSheetSourceSnapshot:
        """Передаёт проверенное текущее состояние для создания и передачи независимых ведомостей."""
        self._validate()
        return InventoryCountSheetSourceSnapshot(
            self.id,
            self.warehouse_id,
            self.owner_id,
            self.scope,
            self.status,
            self.baseline,
            self.updated_at,
            self.version,
        )

    def adjustment_source_snapshot(self) -> InventoryCountAdjustmentSourceSnapshot:
        """Передаёт зарегистрированное основание и результат для производного документа корректировки."""
        self._validate()
        snapshot = InventoryCountAdjustmentSourceSnapshot(
            self.id,
            self.warehouse_id,
            self.owner_id,
            self.scope,
            self.status,
            self.baseline,
            self.result,
            self.updated_at,
            self.version,
        )
        snapshot.ensure_valid()
        return snapshot

    def start(
        self,
        baseline: InventoryCountBaselineSnapshot,
        *,
        expected_version: int,
        warehouse: WarehouseSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
        updated_at: datetime,
    ) -> Self:
        """Запускает подтверждённый план, фиксируя только ссылку на проверенное отдельное основание."""
        normalized = self._prepare_transition(
            expected_version, updated_at, required_status=InventoryCountStatus.CONFIRMED
        )
        InventoryCountStartPolicy.ensure_compatible(
            plan=self.start_plan_snapshot(),
            baseline=baseline,
            warehouse=warehouse,
            locations=locations,
        )
        if baseline.snapshot_at > normalized:
            raise InventoryCountTimeError(
                "Учётный снимок не может быть позже регистрации запуска."
            )
        return self._changed(
            status=InventoryCountStatus.IN_PROGRESS,
            baseline=InventoryCountBaselineRefVO(baseline.id, baseline.snapshot_at),
            updated_at=normalized,
        )

    def register_result(
        self,
        result: InventoryCountResultSnapshot,
        *,
        expected_version: int,
        updated_at: datetime,
        baseline: InventoryCountBaselineSnapshot,
        sheets: tuple[CountSheetReconciliationSnapshot, ...],
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        warehouse: WarehouseSnapshot | None = None,
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> Self:
        """Фиксирует только ссылку на заново проверенный сводный результат без проведения расхождений."""
        updated = self._prepare_transition(
            expected_version,
            updated_at,
            required_status=InventoryCountStatus.IN_PROGRESS,
        )
        InventoryCountResultPolicy.ensure_compatible(
            result=result,
            inventory_count=self.sheet_source_snapshot(),
            baseline=baseline,
            sheets=sheets,
            inventory_items=inventory_items,
            locations=locations,
            positions=positions,
            warehouse=warehouse,
            lots=lots,
            serials=serials,
        )
        if result.prepared_at > updated:
            raise InventoryCountTimeError(
                "Регистрация не может предшествовать подготовке результата."
            )
        return self._changed(
            status=InventoryCountStatus.COUNTED,
            result=InventoryCountResultRefVO(result.id, result.prepared_at),
            updated_at=updated,
        )

    def complete_with_adjustment(
        self,
        *,
        result: InventoryCountResultSnapshot,
        document: StockDocumentAdjustmentCompletionSnapshot,
        execution: StockAdjustmentExecutionSnapshot,
        posting: StockPostingSnapshot,
        application: StockAdjustmentApplicationSnapshot,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Завершает COUNTED по полной исторической цепочке применения без чтения живых остатков."""
        normalized = self._prepare_transition(
            expected_version, updated_at, required_status=InventoryCountStatus.COUNTED
        )
        completion = InventoryCountCompletionPolicy.with_adjustment(
            inventory_count=self.adjustment_source_snapshot(),
            result=result,
            document=document,
            execution=execution,
            posting=posting,
            application=application,
            completed_at=normalized,
        )
        return self._changed(
            status=InventoryCountStatus.COMPLETED,
            completion=completion,
            updated_at=normalized,
        )

    def complete_without_adjustment(
        self,
        *,
        result: InventoryCountResultSnapshot,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Закрывает полностью совпавший зарегистрированный результат без фиктивных документов, позиций или Ledger."""
        normalized = self._prepare_transition(
            expected_version, updated_at, required_status=InventoryCountStatus.COUNTED
        )
        completion = InventoryCountCompletionPolicy.without_adjustment(
            inventory_count=self.adjustment_source_snapshot(),
            result=result,
            completed_at=normalized,
        )
        return self._changed(
            status=InventoryCountStatus.COMPLETED,
            completion=completion,
            updated_at=normalized,
        )

    def _prepare_transition(
        self,
        expected_version: int,
        updated_at: datetime,
        *,
        required_status: InventoryCountStatus = InventoryCountStatus.DRAFT,
    ) -> datetime:
        """Проверяет строгие версии до арифметики, собственный состав, нужный статус и время."""
        if (
            type(self.version) is not int
            or self.version < 0
            or type(expected_version) is not int
            or expected_version < 0
        ):
            raise InvalidInventoryCountValueError(
                "Версии должны быть целыми неотрицательными без bool."
            )
        if self.version != expected_version:
            raise InventoryCountVersionConflictError(
                "Ожидаемая версия инвентаризации устарела."
            )
        self._validate()
        if self.status is not required_status:
            raise InventoryCountStatusError(
                "Статус инвентаризации не допускает эту операцию."
            )
        normalized = normalize_inventory_count_time(updated_at)
        if normalized < self.updated_at:
            raise InventoryCountTimeError("Время изменения не может убывать.")
        return normalized

    def _changed(self, *, updated_at: datetime, **changes: object) -> Self:
        """Создаёт независимый проверенный экземпляр следующей версии."""
        candidate = replace(
            self, **changes, updated_at=updated_at, version=self.version + 1
        )
        candidate._validate()
        return candidate

    def _validate(self) -> None:
        """Проверяет собственные типы, область и UTC-хронологию без текущего состояния других агрегатов."""
        if (
            not isinstance(self.id, InventoryCountIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.scope, CountScopeVO)
            or not isinstance(self.status, InventoryCountStatus)
            or (
                self.baseline is not None
                and not isinstance(self.baseline, InventoryCountBaselineRefVO)
            )
            or (
                self.result is not None
                and not isinstance(self.result, InventoryCountResultRefVO)
            )
            or (
                self.completion is not None
                and not isinstance(self.completion, InventoryCountCompletionVO)
            )
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidInventoryCountValueError(
                "Нужен типизированный собственный состав плана инвентаризации."
            )
        self.scope.ensure_valid()
        created = normalize_inventory_count_time(self.created_at)
        updated = normalize_inventory_count_time(self.updated_at)
        if (
            self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or updated < created
        ):
            raise InventoryCountTimeError(
                "Нужно UTC-время изменения не раньше создания."
            )
        if (
            self.status
            in (
                InventoryCountStatus.IN_PROGRESS,
                InventoryCountStatus.COUNTED,
                InventoryCountStatus.COMPLETED,
            )
        ) != (self.baseline is not None):
            raise InvalidInventoryCountValueError(
                "Основание обязательно для IN_PROGRESS, COUNTED и COMPLETED."
            )
        if self.baseline is not None:
            self.baseline.ensure_valid()
            if not created <= self.baseline.snapshot_at <= updated:
                raise InventoryCountTimeError(
                    "Момент основания должен находиться между созданием и изменением инвентаризации."
                )
        if (
            self.status
            in (InventoryCountStatus.COUNTED, InventoryCountStatus.COMPLETED)
        ) != (self.result is not None):
            raise InvalidInventoryCountValueError(
                "Ссылка на результат обязательна для COUNTED и COMPLETED."
            )
        if self.result is not None:
            self.result.ensure_valid()
            if (
                self.baseline is None
                or not self.baseline.snapshot_at <= self.result.prepared_at <= updated
            ):
                raise InventoryCountTimeError(
                    "Подготовка результата должна находиться между основанием и текущим состоянием."
                )
        if (self.status is InventoryCountStatus.COMPLETED) != (
            self.completion is not None
        ):
            raise InvalidInventoryCountValueError(
                "Сведения о завершении обязательны только для COMPLETED."
            )
        if self.completion is not None:
            self.completion.ensure_valid()
            if not self.result.prepared_at <= self.completion.completed_at <= updated:
                raise InventoryCountTimeError(
                    "Завершение должно находиться между результатом и последним изменением корня."
                )
