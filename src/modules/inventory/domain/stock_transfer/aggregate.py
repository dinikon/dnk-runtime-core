from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Self

from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.stock_transfer_confirmation import (
    StockTransferConfirmationPolicy,
)
from src.modules.inventory.domain.stock_transfer.entity.transfer_line import (
    TransferLine,
)
from src.modules.inventory.domain.stock_transfer.error import (
    EmptyStockTransferError,
    InvalidStockTransferLineError,
    InvalidStockTransferValueError,
    StockTransferLineConflictError,
    StockTransferLineNotFoundError,
    StockTransferSameWarehouseError,
    StockTransferStatusError,
    StockTransferTimeError,
    StockTransferVersionConflictError,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
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
class StockTransfer:
    """План перемещения одного владельца между складами без физической отправки, транзита и приёмки."""

    id: StockTransferIdVO
    source_warehouse_id: WarehouseIdVO
    destination_warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    status: StockTransferStatus
    lines: tuple[TransferLine, ...]
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: StockTransferIdVO,
        source_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
        owner_id: StockOwnerIdVO,
        created_at: datetime,
    ) -> Self:
        """Создаёт пустой черновик версии 0 между разными активными складами для явного владельца."""
        if not isinstance(source_warehouse, WarehouseSnapshot) or not isinstance(
            destination_warehouse, WarehouseSnapshot
        ):
            raise InvalidWarehouseSnapshotError(
                "Нужны снимки исходного и целевого складов."
            )
        StockTransferConfirmationPolicy.ensure_warehouses(
            source_warehouse_id=source_warehouse.id,
            destination_warehouse_id=destination_warehouse.id,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
        )
        return cls.restore(
            identifier=identifier,
            source_warehouse_id=source_warehouse.id,
            destination_warehouse_id=destination_warehouse.id,
            owner_id=owner_id,
            status=StockTransferStatus.DRAFT,
            lines=(),
            created_at=created_at,
            updated_at=created_at,
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockTransferIdVO,
        source_warehouse_id: WarehouseIdVO,
        destination_warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        status: StockTransferStatus,
        lines: tuple[TransferLine, ...],
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        """Восстанавливает полный собственный исторический состав без актуальных складов и товаров."""
        transfer = cls(
            identifier,
            source_warehouse_id,
            destination_warehouse_id,
            owner_id,
            status,
            lines,
            cls._normalize_time(created_at),
            cls._normalize_time(updated_at),
            version,
        )
        transfer._validate()
        return transfer

    def add_line(
        self,
        line: TransferLine,
        *,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        updated_at: datetime,
    ) -> Self:
        """Добавляет проверенную плановую строку только в черновик без объединения одинаковых товаров."""
        normalized = self._prepare_transition(expected_version, updated_at)
        if not isinstance(line, TransferLine):
            raise InvalidStockTransferLineError("Нужна дочерняя строка TransferLine.")
        line.ensure_compatible(inventory_item=inventory_item)
        return self._changed(updated_at=normalized, lines=(*self.lines, line))

    def change_line_quantity(
        self,
        *,
        identifier: StockTransferLineIdVO,
        quantity: QuantityVO,
        uom: UomCodeVO,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        updated_at: datetime,
    ) -> Self:
        """Заново пересчитывает ввод черновика с сохранением ID строки, товара и базовой единицы."""
        normalized = self._prepare_transition(expected_version, updated_at)
        previous = self._find_line(identifier)
        conversion = QuantityConversionSnapshotVO.create(
            quantity=quantity, uom=uom, base_uom=previous.base_uom
        )
        changed = TransferLine.restore(
            identifier=previous.id,
            inventory_item_id=previous.inventory_item_id,
            base_uom=previous.base_uom,
            planned_qty=conversion.to_base_quantity(),
            conversion=conversion,
        )
        changed.ensure_compatible(inventory_item=inventory_item)
        return self._changed(
            updated_at=normalized,
            lines=tuple(
                changed if line.id == identifier else line for line in self.lines
            ),
        )

    def remove_line(
        self,
        identifier: StockTransferLineIdVO,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Удаляет строку черновика без текущего товара или проверки физической доступности."""
        normalized = self._prepare_transition(expected_version, updated_at)
        self._find_line(identifier)
        return self._changed(
            updated_at=normalized,
            lines=tuple(line for line in self.lines if line.id != identifier),
        )

    def confirm(
        self,
        *,
        expected_version: int,
        source_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        updated_at: datetime,
    ) -> Self:
        """Фиксирует непустой план после повторной проверки двух складов и текущих правил товаров."""
        normalized = self._prepare_transition(expected_version, updated_at)
        StockTransferConfirmationPolicy.ensure_confirmable(
            source_warehouse_id=self.source_warehouse_id,
            destination_warehouse_id=self.destination_warehouse_id,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
            lines=self.lines,
            inventory_items=inventory_items,
        )
        return self._changed(
            updated_at=normalized, status=StockTransferStatus.CONFIRMED
        )

    def cancel(self, *, expected_version: int, updated_at: datetime) -> Self:
        """Отменяет только черновик с сохранением строк и без освобождения резервов или изменений остатков."""
        normalized = self._prepare_transition(expected_version, updated_at)
        return self._changed(
            updated_at=normalized, status=StockTransferStatus.CANCELLED
        )

    def _prepare_transition(
        self, expected_version: int, updated_at: datetime
    ) -> datetime:
        """Проверяет строгую версию до исторической арифметики, затем собственный состав, черновик и время."""
        if (
            type(self.version) is not int
            or self.version < 0
            or type(expected_version) is not int
            or expected_version < 0
        ):
            raise InvalidStockTransferValueError(
                "Текущая и ожидаемая версии должны быть целыми неотрицательными без bool."
            )
        if expected_version != self.version:
            raise StockTransferVersionConflictError(
                "Ожидаемая версия не совпадает с текущей версией перемещения."
            )
        self._validate()
        if self.status is not StockTransferStatus.DRAFT:
            raise StockTransferStatusError(
                "Редактирование, подтверждение и отмена доступны только черновику перемещения."
            )
        normalized = self._normalize_time(updated_at)
        if normalized < self.updated_at:
            raise StockTransferTimeError(
                "Время изменения не может предшествовать предыдущему изменению."
            )
        return normalized

    def _find_line(self, identifier: StockTransferLineIdVO) -> TransferLine:
        """Находит дочернюю строку данного агрегата по типизированному ID."""
        if not isinstance(identifier, StockTransferLineIdVO):
            raise InvalidStockTransferLineError("Нужен StockTransferLineIdVO.")
        for line in self.lines:
            if line.id == identifier:
                return line
        raise StockTransferLineNotFoundError("Строка отсутствует в данном перемещении.")

    def _changed(self, *, updated_at: datetime, **changes: object) -> Self:
        """Возвращает новый проверенный экземпляр версии +1 либо исходный при равном содержимом."""
        candidate = replace(self, **changes)
        candidate._validate()
        if candidate == self:
            return self
        candidate = replace(candidate, updated_at=updated_at, version=self.version + 1)
        candidate._validate()
        return candidate

    def _validate(self) -> None:
        """Проверяет типы, разные склады, уникальность строк, UTC-хронологию и непустой подтверждённый план."""
        if (
            not isinstance(self.id, StockTransferIdVO)
            or not isinstance(self.source_warehouse_id, WarehouseIdVO)
            or not isinstance(self.destination_warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.status, StockTransferStatus)
            or not isinstance(self.lines, tuple)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidStockTransferValueError(
                "Нужны типизированные поля, tuple строк и целая неотрицательная версия перемещения."
            )
        if self.source_warehouse_id == self.destination_warehouse_id:
            raise StockTransferSameWarehouseError(
                "Исходный и целевой склады должны различаться."
            )
        created, updated = self._normalize_time(self.created_at), self._normalize_time(
            self.updated_at
        )
        if (
            self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or updated < created
        ):
            raise StockTransferTimeError(
                "Сохранённое время должно быть в UTC; изменение не раньше создания."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, TransferLine):
                raise InvalidStockTransferLineError(
                    "Состав перемещения содержит только TransferLine."
                )
            line.ensure_valid()
            if line.id in ids:
                raise StockTransferLineConflictError(
                    "ID строк перемещения должны быть уникальны."
                )
            ids.add(line.id)
        if self.status is StockTransferStatus.CONFIRMED and not self.lines:
            raise EmptyStockTransferError(
                "Подтверждённый план перемещения не может быть пустым."
            )

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        """Нормализует явно переданное aware-время в UTC без обращения к системным часам."""
        if not isinstance(value, datetime):
            raise StockTransferTimeError("Нужен datetime с часовым поясом.")
        try:
            if value.utcoffset() is None:
                raise StockTransferTimeError(
                    "Время перемещения должно содержать часовой пояс."
                )
            return value.astimezone(UTC)
        except (ValueError, OverflowError) as exc:
            raise StockTransferTimeError(
                "Время перемещения невозможно представить в UTC."
            ) from exc
