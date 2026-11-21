from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Self

from src.modules.inventory.domain.count_sheet.reconciliation_snapshot import (
    CountSheetReconciliationSnapshot,
    CountLineReconciliationSnapshot,
)
from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountLineError,
    InvalidCountSheetValueError,
    CountSheetLineConflictError,
    CountSheetLineNotFoundError,
    CountSheetStatusError,
    CountSheetTimeError,
    CountSheetVersionConflictError,
    UncountedCountSheetError,
)
from src.modules.inventory.domain.count_sheet.time import normalize_count_sheet_time
from src.modules.inventory.domain.count_sheet.value_object.identifier import (
    CountSheetIdVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_binding import (
    CountSheetLineBindingVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.policy.found_count_line import FoundCountLinePolicy
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.count_sheet.value_object.status import (
    CountSheetStatus,
)
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.sheet_source_snapshot import (
    InventoryCountSheetSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.count_sheet_line import CountSheetLinePolicy
from src.modules.inventory.domain.policy.count_sheet_source import (
    CountSheetSourcePolicy,
)
from src.modules.inventory.domain.policy.count_sheet_submission import (
    CountSheetSubmissionPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class CountSheet:
    """Самостоятельная ведомость с неизменными учётными строками и наблюдениями найденного запаса без изменения остатков."""

    id: CountSheetIdVO
    inventory_count_id: InventoryCountIdVO
    baseline: InventoryCountBaselineRefVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    status: CountSheetStatus
    lines: tuple[CountLine, ...]
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create_from_baseline(
        cls,
        *,
        identifier: CountSheetIdVO,
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        bindings: tuple[CountSheetLineBindingVO, ...],
        created_at: datetime,
    ) -> Self:
        """Создаёт непустой черновик версии 0 с фиксированными выбранными позициями и отсутствующими фактами."""
        lines = CountSheetSourcePolicy.build_lines(
            inventory_count=inventory_count, baseline=baseline, bindings=bindings
        )
        created = normalize_count_sheet_time(created_at)
        if created < inventory_count.updated_at:
            raise CountSheetTimeError(
                "Ведомость не может быть создана раньше текущего состояния родителя."
            )
        return cls.restore(
            identifier=identifier,
            inventory_count_id=inventory_count.id,
            baseline=InventoryCountBaselineRefVO(baseline.id, baseline.snapshot_at),
            warehouse_id=inventory_count.warehouse_id,
            owner_id=inventory_count.owner_id,
            status=CountSheetStatus.DRAFT,
            lines=lines,
            created_at=created,
            updated_at=created,
            version=0,
        )

    @classmethod
    def create_with_found_line(
        cls,
        *,
        identifier: CountSheetIdVO,
        line_id: CountLineIdVO,
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        dimensions: StockDimensionsVO,
        inventory_item: InventoryItemStockSnapshot,
        warehouse: WarehouseSnapshot,
        location: StockLocationSnapshot,
        created_at: datetime,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> Self:
        """Создаёт непустой черновик версии 0 с первой FOUND-строкой, в том числе при пустом наборе позиций основания."""
        CountSheetSourcePolicy.ensure_compatible(
            inventory_count=inventory_count, baseline=baseline
        )
        line = FoundCountLinePolicy.build_line(
            identifier=line_id,
            dimensions=dimensions,
            baseline=baseline,
            inventory_item=inventory_item,
            warehouse=warehouse,
            location=location,
            lot=lot,
            serial=serial,
        )
        created = normalize_count_sheet_time(created_at)
        if created < inventory_count.updated_at:
            raise CountSheetTimeError(
                "Ведомость не может быть создана раньше текущего состояния родителя."
            )
        return cls.restore(
            identifier=identifier,
            inventory_count_id=inventory_count.id,
            baseline=InventoryCountBaselineRefVO(baseline.id, baseline.snapshot_at),
            warehouse_id=inventory_count.warehouse_id,
            owner_id=inventory_count.owner_id,
            status=CountSheetStatus.DRAFT,
            lines=(line,),
            created_at=created,
            updated_at=created,
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: CountSheetIdVO,
        inventory_count_id: InventoryCountIdVO,
        baseline: InventoryCountBaselineRefVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        status: CountSheetStatus,
        lines: tuple[CountLine, ...],
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        """Восстанавливает собственную историю без текущего родителя, товаров и большого основания."""
        sheet = cls(
            identifier,
            inventory_count_id,
            baseline,
            warehouse_id,
            owner_id,
            status,
            lines,
            normalize_count_sheet_time(created_at),
            normalize_count_sheet_time(updated_at),
            version,
        )
        sheet._validate()
        return sheet

    def record_count(
        self,
        identifier: CountLineIdVO,
        *,
        counted_qty: QuantityVO,
        counted_at: datetime,
        inventory_item: InventoryItemStockSnapshot,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Фиксирует или исправляет наблюдение в базовой единице только в черновике по текущим правилам товара."""
        updated = self._prepare_transition(expected_version, updated_at)
        previous = self.get_line(identifier)
        CountSheetLinePolicy.ensure_compatible(
            line=previous, inventory_item=inventory_item, quantity=counted_qty
        )
        counted = normalize_count_sheet_time(counted_at)
        if not self.created_at <= counted <= updated:
            raise CountSheetTimeError(
                "Пересчёт должен находиться между созданием ведомости и регистрацией изменения."
            )
        changed = previous.record_count(quantity=counted_qty, counted_at=counted)
        if changed == previous:
            return self
        return self._changed(
            updated_at=updated,
            lines=tuple(
                changed if line.id == identifier else line for line in self.lines
            ),
        )

    def add_found_line(
        self,
        identifier: CountLineIdVO,
        *,
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        dimensions: StockDimensionsVO,
        inventory_item: InventoryItemStockSnapshot,
        warehouse: WarehouseSnapshot,
        location: StockLocationSnapshot,
        expected_version: int,
        updated_at: datetime,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> Self:
        """Дополняет только черновик новыми непосчитанными измерениями после повторной проверки родителя и основания."""
        updated = self._prepare_transition(expected_version, updated_at)
        CountSheetSourcePolicy.ensure_sheet_source(
            inventory_count_id=self.inventory_count_id,
            warehouse_id=self.warehouse_id,
            owner_id=self.owner_id,
            baseline_ref=self.baseline,
            lines=self.lines,
            inventory_count=inventory_count,
            baseline=baseline,
        )
        if updated < inventory_count.updated_at:
            raise CountSheetTimeError(
                "Добавление строки не может предшествовать текущему состоянию родителя."
            )
        line = FoundCountLinePolicy.build_line(
            identifier=identifier,
            dimensions=dimensions,
            baseline=baseline,
            inventory_item=inventory_item,
            warehouse=warehouse,
            location=location,
            lot=lot,
            serial=serial,
        )
        return self._changed(
            updated_at=updated,
            lines=tuple(sorted((*self.lines, line), key=lambda row: row.id.uuid.int)),
        )

    def submit(
        self,
        *,
        expected_version: int,
        updated_at: datetime,
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        warehouse: WarehouseSnapshot | None = None,
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> Self:
        """Передаёт полностью посчитанную ведомость после проверки родителя, строк, товаров и всего актуального основания."""
        updated = self._prepare_transition(expected_version, updated_at)
        CountSheetSubmissionPolicy.ensure_submittable(
            inventory_count_id=self.inventory_count_id,
            warehouse_id=self.warehouse_id,
            owner_id=self.owner_id,
            baseline_ref=self.baseline,
            lines=self.lines,
            inventory_count=inventory_count,
            baseline=baseline,
            inventory_items=inventory_items,
            locations=locations,
            positions=positions,
            submitted_at=updated,
            warehouse=warehouse,
            lots=lots,
            serials=serials,
        )
        return self._changed(updated_at=updated, status=CountSheetStatus.SUBMITTED)

    def cancel(self, *, expected_version: int, updated_at: datetime) -> Self:
        """Отменяет только черновик, сохраняя строки и результаты без текущих внешних снимков."""
        updated = self._prepare_transition(expected_version, updated_at)
        return self._changed(updated_at=updated, status=CountSheetStatus.CANCELLED)

    def withdraw(
        self,
        *,
        inventory_count: InventoryCountSheetSourceSnapshot,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Отзывает только переданную ведомость до фиксации общего результата, сохраняя все наблюдения."""
        updated = self._prepare_transition(
            expected_version, updated_at, required_status=CountSheetStatus.SUBMITTED
        )
        CountSheetSourcePolicy.ensure_parent(
            inventory_count_id=self.inventory_count_id,
            warehouse_id=self.warehouse_id,
            owner_id=self.owner_id,
            baseline_ref=self.baseline,
            inventory_count=inventory_count,
        )
        if updated < inventory_count.updated_at:
            raise CountSheetTimeError(
                "Отзыв не может предшествовать текущему состоянию родителя."
            )
        return self._changed(updated_at=updated, status=CountSheetStatus.WITHDRAWN)

    def reconciliation_snapshot(self) -> CountSheetReconciliationSnapshot:
        """Возвращает проверенный снимок ведомости и значений строк для сводного результата."""
        self._validate()
        return CountSheetReconciliationSnapshot(
            self.id,
            self.inventory_count_id,
            self.baseline,
            self.warehouse_id,
            self.owner_id,
            self.status,
            tuple(
                CountLineReconciliationSnapshot(
                    line.id,
                    line.origin,
                    line.position_id,
                    line.dimensions,
                    line.base_uom,
                    line.expected_qty,
                    line.position_version,
                    line.counted_qty,
                    line.counted_at,
                )
                for line in self.lines
            ),
            self.created_at,
            self.updated_at,
            self.version,
        )

    def get_line(self, identifier: CountLineIdVO) -> CountLine:
        """Находит дочернюю строку только в данной ведомости по типизированному ID."""
        if not isinstance(identifier, CountLineIdVO):
            raise InvalidCountLineError("Нужен CountLineIdVO.")
        for line in self.lines:
            if line.id == identifier:
                return line
        raise CountSheetLineNotFoundError("Строка отсутствует в ведомости.")

    def _prepare_transition(
        self,
        expected_version: int,
        updated_at: datetime,
        *,
        required_status: CountSheetStatus = CountSheetStatus.DRAFT,
    ) -> datetime:
        """Проверяет версии до арифметики, собственные инварианты, допустимый статус и неубывающее время регистрации."""
        if (
            type(self.version) is not int
            or self.version < 0
            or type(expected_version) is not int
            or expected_version < 0
        ):
            raise InvalidCountSheetValueError(
                "Версии должны быть целыми неотрицательными без bool."
            )
        if self.version != expected_version:
            raise CountSheetVersionConflictError("Ожидаемая версия ведомости устарела.")
        self._validate()
        if self.status is not required_status:
            raise CountSheetStatusError("Статус ведомости не допускает эту операцию.")
        updated = normalize_count_sheet_time(updated_at)
        if updated < self.updated_at:
            raise CountSheetTimeError("Время регистрации изменений не может убывать.")
        return updated

    def _changed(self, *, updated_at: datetime, **changes: object) -> Self:
        """Возвращает независимый проверенный экземпляр следующей версии без изменения источников."""
        changed = replace(
            self, **changes, updated_at=updated_at, version=self.version + 1
        )
        changed._validate()
        return changed

    def _validate(self) -> None:
        """Проверяет собственный непустой состав, уникальность строк, UTC, владельца и заполненность переданной ведомости."""
        if (
            not isinstance(self.id, CountSheetIdVO)
            or not isinstance(self.inventory_count_id, InventoryCountIdVO)
            or not isinstance(self.baseline, InventoryCountBaselineRefVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.status, CountSheetStatus)
            or not isinstance(self.lines, tuple)
            or not self.lines
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidCountSheetValueError(
                "Нужен типизированный непустой собственный состав ведомости."
            )
        self.baseline.ensure_valid()
        created, updated = normalize_count_sheet_time(
            self.created_at
        ), normalize_count_sheet_time(self.updated_at)
        if (
            self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or not self.baseline.snapshot_at <= created <= updated
        ):
            raise CountSheetTimeError(
                "Нужна UTC-хронология: основание, создание ведомости, регистрация изменения."
            )
        ids, positions, dimensions = set(), set(), set()
        for line in self.lines:
            if not isinstance(line, CountLine):
                raise InvalidCountLineError("Нужен tuple дочерних CountLine.")
            line.ensure_valid()
            if (
                line.id in ids
                or (line.position_id is not None and line.position_id in positions)
                or line.dimensions in dimensions
            ):
                raise CountSheetLineConflictError(
                    "ID строк, позиции и измерения должны быть уникальны."
                )
            ids.add(line.id)
            if line.position_id is not None:
                positions.add(line.position_id)
            dimensions.add(line.dimensions)
            if line.dimensions.owner_id != self.owner_id:
                raise InvalidCountSheetValueError(
                    "Владелец каждой строки должен соответствовать ведомости."
                )
            if (
                line.counted_at is not None
                and not created <= line.counted_at <= updated
            ):
                raise CountSheetTimeError(
                    "Момент пересчёта строки вне хронологии ведомости."
                )
            if (
                self.status in (CountSheetStatus.SUBMITTED, CountSheetStatus.WITHDRAWN)
                and line.counted_qty is None
            ):
                raise UncountedCountSheetError(
                    "Переданная ведомость должна содержать только посчитанные строки."
                )
