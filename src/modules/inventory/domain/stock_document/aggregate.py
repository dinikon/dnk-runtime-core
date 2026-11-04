from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID

from src.modules.inventory.domain.policy.stock_transfer_dispatch_document import (
    StockTransferDispatchDocumentPolicy,
)
from src.modules.inventory.domain.stock_transfer.dispatch_document_snapshot import (
    StockTransferDispatchDocumentSnapshot,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_document.transfer_dispatch_snapshot import (
    StockDocumentTransferDispatchSnapshot,
    StockDocumentTransferDispatchLineSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.transfer_dispatch_line_binding import (
    StockTransferDispatchDocumentLineBindingVO,
)

from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.shipment_document import ShipmentDocumentPolicy
from src.modules.inventory.domain.shipment.document_snapshot import (
    ShipmentDocumentSnapshot,
)
from src.modules.inventory.domain.policy.stock_document_progress import (
    StockDocumentProgressPolicy,
)
from src.modules.inventory.domain.policy.stock_execution_document import (
    StockExecutionDocumentPolicy,
)
from src.modules.inventory.domain.stock_document.execution_snapshot import (
    StockDocumentExecutionSnapshot,
    StockDocumentLineExecutionSnapshot,
)
from src.modules.inventory.domain.stock_execution.document_snapshot import (
    StockExecutionDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.policy.stock_document_confirmation import (
    StockDocumentConfirmationPolicy,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentLineError,
    InvalidStockDocumentValueError,
    StockDocumentLineConflictError,
    StockDocumentLineNotFoundError,
    StockDocumentNotDraftError,
    StockDocumentTimeError,
    StockDocumentShipmentMismatchError,
    StockDocumentTransferDispatchMismatchError,
)
from src.modules.inventory.domain.stock_document.shipment_snapshot import (
    StockDocumentShipmentLineSnapshot,
    StockDocumentShipmentSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_document.value_object.shipment_line_binding import (
    ShipmentDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockDocument:
    """План складской операции с накопленным прогрессом строк без журнала, резервов и физических остатков."""

    id: StockDocumentIdVO
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    source: DocumentSourceVO | None
    status: StockDocumentStatus
    lines: tuple[StockDocumentLine, ...]
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: StockDocumentIdVO,
        operation_type: StockOperationType,
        warehouse: WarehouseSnapshot,
        owner_id: StockOwnerIdVO,
        created_at: datetime,
        source: DocumentSourceVO | None = None,
    ) -> Self:
        """Создаёт пустой черновик версии 0 для явно указанного владельца и активного склада."""
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError(
                "Нужен снимок склада для создания документа."
            )
        StockDocumentConfirmationPolicy.ensure_warehouse(
            warehouse_id=warehouse.id, warehouse=warehouse
        )
        return cls.restore(
            identifier=identifier,
            operation_type=operation_type,
            warehouse_id=warehouse.id,
            owner_id=owner_id,
            source=source,
            status=StockDocumentStatus.DRAFT,
            lines=(),
            created_at=created_at,
            updated_at=created_at,
            version=0,
        )

    @classmethod
    def create_from_shipment(
        cls,
        *,
        identifier: StockDocumentIdVO,
        shipment: ShipmentDocumentSnapshot,
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        line_bindings: tuple[ShipmentDocumentLineBindingVO, ...],
        created_at: datetime,
    ) -> Self:
        """Создаёт готовый черновик ISSUE версии 0 на все открытые остатки отправления без его изменения."""
        normalized = cls._normalize_time(created_at)
        lines = ShipmentDocumentPolicy.build_lines(
            shipment=shipment,
            warehouse=warehouse,
            inventory_items=inventory_items,
            line_bindings=line_bindings,
            as_of=normalized,
        )
        return cls.restore(
            identifier=identifier,
            operation_type=StockOperationType.ISSUE,
            warehouse_id=shipment.warehouse_id,
            owner_id=shipment.owner_id,
            source=DocumentSourceVO(
                ShipmentDocumentPolicy.SOURCE_SYSTEM,
                str(shipment.id.uuid),
                shipment.version,
            ),
            status=StockDocumentStatus.DRAFT,
            lines=lines,
            created_at=normalized,
            updated_at=normalized,
            version=0,
        )

    @classmethod
    def create_from_stock_transfer_dispatch(
        cls,
        *,
        identifier: StockDocumentIdVO,
        operation_type: StockOperationType,
        transfer: StockTransferDispatchDocumentSnapshot,
        source_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
        transit_warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        line_bindings: tuple[StockTransferDispatchDocumentLineBindingVO, ...],
        created_at: datetime,
    ) -> Self:
        """Строит самостоятельный черновик ISSUE A или RECEIPT T на весь открытый остаток одной версии перемещения."""
        normalized = cls._normalize_time(created_at)
        lines = StockTransferDispatchDocumentPolicy.build_lines(
            transfer=transfer,
            operation_type=operation_type,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
            transit_warehouse=transit_warehouse,
            inventory_items=inventory_items,
            line_bindings=line_bindings,
            as_of=normalized,
        )
        return cls.restore(
            identifier=identifier,
            operation_type=operation_type,
            warehouse_id=(
                transfer.source_warehouse_id
                if operation_type is StockOperationType.ISSUE
                else transit_warehouse.id
            ),
            owner_id=transfer.owner_id,
            source=DocumentSourceVO(
                StockTransferDispatchDocumentPolicy.source_system(operation_type),
                str(transfer.id.uuid),
                transfer.version,
            ),
            status=StockDocumentStatus.DRAFT,
            lines=lines,
            created_at=normalized,
            updated_at=normalized,
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockDocumentIdVO,
        operation_type: StockOperationType,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        source: DocumentSourceVO | None,
        status: StockDocumentStatus,
        lines: tuple[StockDocumentLine, ...],
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        """Восстанавливает полный собственный состав без текущих товаров, склада и I/O."""
        document = cls(
            identifier,
            operation_type,
            warehouse_id,
            owner_id,
            source,
            status,
            lines,
            cls._normalize_time(created_at),
            cls._normalize_time(updated_at),
            version,
        )
        document._validate()
        return document

    def add_line(
        self,
        line: StockDocumentLine,
        *,
        inventory_item: InventoryItemDocumentSnapshot,
        updated_at: datetime,
    ) -> Self:
        """Добавляет проверенную плановую строку только в черновик без скрытого объединения товаров."""
        self._ensure_draft()
        if not isinstance(line, StockDocumentLine):
            raise InvalidStockDocumentLineError(
                "Добавлять можно только StockDocumentLine."
            )
        line.ensure_compatible(inventory_item)
        return self._with_changes(updated_at=updated_at, lines=(*self.lines, line))

    def change_line(
        self,
        *,
        identifier: StockDocumentLineIdVO,
        quantity: QuantityVO,
        uom: UomCodeVO,
        inventory_item: InventoryItemDocumentSnapshot,
        updated_at: datetime,
    ) -> Self:
        """Меняет количество строки черновика, сохраняя её ID, товар, исторический SKU и базовую единицу."""
        self._ensure_draft()
        original = self._find_line(identifier)
        conversion = QuantityConversionSnapshotVO.create(
            quantity=quantity, uom=uom, base_uom=original.base_uom
        )
        changed = StockDocumentLine.restore(
            identifier=original.id,
            inventory_item_id=original.inventory_item_id,
            sku=original.sku,
            base_uom=original.base_uom,
            planned_qty=conversion.to_base_quantity(),
            conversion=conversion,
            executed_qty=original.executed_qty,
            source=original.source,
        )
        changed.ensure_compatible(inventory_item)
        return self._with_changes(
            updated_at=updated_at,
            lines=tuple(
                changed if line.id == identifier else line for line in self.lines
            ),
        )

    def remove_line(
        self, identifier: StockDocumentLineIdVO, *, updated_at: datetime
    ) -> Self:
        """Удаляет существующую строку черновика, допуская снова пустой план."""
        self._ensure_draft()
        self._find_line(identifier)
        return self._with_changes(
            updated_at=updated_at,
            lines=tuple(line for line in self.lines if line.id != identifier),
        )

    def get_line(self, identifier: StockDocumentLineIdVO) -> StockDocumentLine:
        """Возвращает собственную неизменяемую строку по её типизированному идентификатору."""
        self._validate()
        return self._find_line(identifier)

    def confirm(
        self,
        *,
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        updated_at: datetime,
        shipment: ShipmentDocumentSnapshot | None = None,
        transfer: StockTransferDispatchDocumentSnapshot | None = None,
        companion_document: StockDocumentTransferDispatchSnapshot | None = None,
        transfer_warehouses: tuple[WarehouseSnapshot, ...] | None = None,
    ) -> Self:
        """Фиксирует непустой совместимый план без проведения, резервирования и изменения остатков."""
        self._ensure_draft()
        StockDocumentConfirmationPolicy.ensure_confirmable(
            warehouse_id=self.warehouse_id,
            warehouse=warehouse,
            lines=self.lines,
            inventory_items=inventory_items,
        )
        normalized = self._normalize_time(updated_at)
        ShipmentDocumentPolicy.ensure_confirmable(
            operation_type=self.operation_type,
            source=self.source,
            warehouse_id=self.warehouse_id,
            owner_id=self.owner_id,
            lines=self.lines,
            shipment=shipment,
            as_of=normalized,
        )
        linked_transfer = self.source is not None and self.source.system in (
            StockTransferDispatchDocumentPolicy.ISSUE_SOURCE_SYSTEM,
            StockTransferDispatchDocumentPolicy.RECEIPT_SOURCE_SYSTEM,
        )
        StockTransferDispatchDocumentPolicy.ensure_confirmable(
            document=self.transfer_dispatch_snapshot() if linked_transfer else None,
            transfer=transfer,
            companion=companion_document,
            warehouses=transfer_warehouses,
            as_of=normalized,
        )
        return self._with_changes(
            updated_at=normalized, status=StockDocumentStatus.CONFIRMED
        )

    def cancel(self, *, updated_at: datetime) -> Self:
        """Отменяет черновик или подтверждённый план без исполненных количеств."""
        self._validate()
        if self.status not in (
            StockDocumentStatus.DRAFT,
            StockDocumentStatus.CONFIRMED,
        ):
            raise StockDocumentNotDraftError(
                "Отмена доступна черновику или подтверждённому плану без исполнения."
            )
        return self._with_changes(
            updated_at=updated_at, status=StockDocumentStatus.CANCELLED
        )

    def shipment_snapshot(self) -> StockDocumentShipmentSnapshot:
        """Передаёт проверенное происхождение строк и прогресс документа без ручного разбора ссылок вызывающим кодом."""
        self._validate()
        if (
            self.source is None
            or self.source.system != ShipmentDocumentPolicy.SOURCE_SYSTEM
        ):
            raise StockDocumentShipmentMismatchError(
                "Документ не имеет основания Shipment."
            )
        return StockDocumentShipmentSnapshot(
            self.id,
            self.version,
            self.status,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.updated_at,
            ShipmentIdVO(UUID(self.source.reference)),
            self.source.version,
            tuple(
                StockDocumentShipmentLineSnapshot(
                    line.id,
                    ShipmentLineIdVO(UUID(line.source.reference)),
                    line.inventory_item_id,
                    line.base_uom,
                    line.planned_qty,
                    line.executed_qty,
                )
                for line in self.lines
            ),
        )

    def transfer_dispatch_snapshot(self) -> StockDocumentTransferDispatchSnapshot:
        """Передаёт собственный прогресс и проверенные основания отправки без загрузки StockTransfer или второго документа."""
        self._validate()
        if self.source is None or self.source.system not in (
            StockTransferDispatchDocumentPolicy.ISSUE_SOURCE_SYSTEM,
            StockTransferDispatchDocumentPolicy.RECEIPT_SOURCE_SYSTEM,
        ):
            raise StockDocumentTransferDispatchMismatchError(
                "Документ не имеет основания отправки StockTransfer."
            )
        return StockDocumentTransferDispatchSnapshot(
            self.id,
            self.version,
            self.status,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.updated_at,
            StockTransferIdVO(UUID(self.source.reference)),
            self.source.version,
            tuple(
                StockDocumentTransferDispatchLineSnapshot(
                    line.id,
                    StockTransferLineIdVO(UUID(line.source.reference)),
                    line.inventory_item_id,
                    line.base_uom,
                    line.planned_qty,
                    line.executed_qty,
                )
                for line in self.lines
            ),
        )

    def execution_snapshot(self) -> StockDocumentExecutionSnapshot:
        """Возвращает текущую версию и остатки каждой плановой строки без коллекции исполнений."""
        self._validate()
        return StockDocumentExecutionSnapshot(
            self.id,
            self.operation_type,
            self.warehouse_id,
            self.owner_id,
            self.status,
            self.version,
            self.updated_at,
            tuple(
                StockDocumentLineExecutionSnapshot(
                    line.id,
                    line.inventory_item_id,
                    line.base_uom,
                    line.planned_qty,
                    line.executed_qty,
                )
                for line in self.lines
            ),
        )

    def register_execution(
        self, execution: StockExecutionDocumentSnapshot, *, updated_at: datetime
    ) -> Self:
        """Регистрирует суммарное исполнение по строкам текущей версии плана без изменения физического остатка."""
        self._validate()
        StockExecutionDocumentPolicy.ensure_compatible(
            document=self.execution_snapshot(), execution=execution
        )
        if self._normalize_time(updated_at) < execution.executed_at:
            raise StockDocumentTimeError(
                "Регистрация не может быть раньше самого исполнения."
            )
        by_id = {line.document_line_id: line.quantity for line in execution.lines}
        lines = tuple(
            (
                replace(
                    line,
                    executed_qty=QuantityArithmeticPolicy.add(
                        line.executed_qty, by_id[line.id]
                    ),
                )
                if line.id in by_id
                else line
            )
            for line in self.lines
        )
        status = (
            StockDocumentStatus.COMPLETED
            if all(line.planned_qty == line.executed_qty for line in lines)
            else StockDocumentStatus.PARTIALLY_EXECUTED
        )
        return self._with_changes(updated_at=updated_at, lines=lines, status=status)

    def _with_changes(self, *, updated_at: datetime, **changes: object) -> Self:
        """Возвращает новый проверенный экземпляр с версией +1, сохраняя объект при отсутствии изменений."""
        normalized = self._normalize_time(updated_at)
        if normalized < self.updated_at:
            raise StockDocumentTimeError(
                "Время изменения не может быть раньше предыдущего изменения."
            )
        candidate = replace(self, **changes)
        candidate._validate()
        if candidate == self:
            return self
        candidate = replace(candidate, updated_at=normalized, version=self.version + 1)
        candidate._validate()
        return candidate

    def _ensure_draft(self) -> None:
        """Проверяет собственное состояние перед разрешением изменить только черновой план."""
        self._validate()
        if self.status is not StockDocumentStatus.DRAFT:
            raise StockDocumentNotDraftError(
                "Редактирование строк и подтверждение доступны только черновику."
            )

    def _find_line(self, identifier: StockDocumentLineIdVO) -> StockDocumentLine:
        """Находит строку данного документа без доступа к отдельному хранилищу Entity."""
        if not isinstance(identifier, StockDocumentLineIdVO):
            raise InvalidStockDocumentLineError("Нужен StockDocumentLineIdVO.")
        for line in self.lines:
            if line.id == identifier:
                return line
        raise StockDocumentLineNotFoundError("Строка отсутствует в документе.")

    def _validate(self) -> None:
        """Проверяет собственные типы, состав, UTC-хронологию и непустой подтверждённый план."""
        if (
            not isinstance(self.id, StockDocumentIdVO)
            or not isinstance(self.operation_type, StockOperationType)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or (
                self.source is not None
                and not isinstance(self.source, DocumentSourceVO)
            )
            or not isinstance(self.status, StockDocumentStatus)
            or not isinstance(self.lines, tuple)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidStockDocumentValueError(
                "Нужны типизированные поля, tuple строк и целая неотрицательная версия документа."
            )
        created = self._normalize_time(self.created_at)
        updated = self._normalize_time(self.updated_at)
        if (
            self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or updated < created
        ):
            raise StockDocumentTimeError(
                "Сохранённые даты должны быть в UTC; изменение не раньше создания."
            )
        line_ids = set()
        for line in self.lines:
            if not isinstance(line, StockDocumentLine):
                raise InvalidStockDocumentLineError(
                    "Состав документа содержит только StockDocumentLine."
                )
            line.ensure_valid()
            if line.id in line_ids:
                raise StockDocumentLineConflictError(
                    "ID строк документа должны быть уникальны."
                )
            line_ids.add(line.id)
        ShipmentDocumentPolicy.ensure_document_source(
            operation_type=self.operation_type,
            source=self.source,
            lines=self.lines,
        )
        StockTransferDispatchDocumentPolicy.ensure_document_source(
            operation_type=self.operation_type,
            source=self.source,
            lines=self.lines,
        )
        StockDocumentProgressPolicy.ensure_valid(
            status=self.status,
            quantities=tuple(
                (line.planned_qty, line.executed_qty) for line in self.lines
            ),
        )

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        """Требует явный часовой пояс и нормализует переданное время без обращения к часам."""
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise StockDocumentTimeError(
                "Время документа должно содержать часовой пояс."
            )
        try:
            return value.astimezone(UTC)
        except (ValueError, OverflowError) as exc:
            raise StockDocumentTimeError(
                "Время документа невозможно представить в UTC."
            ) from exc
