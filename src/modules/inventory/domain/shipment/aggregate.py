from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Self

from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.shipment_confirmation import (
    ShipmentConfirmationPolicy,
)
from src.modules.inventory.domain.policy.shipment_line import ShipmentLinePolicy
from src.modules.inventory.domain.shipment.entity.shipment_line import ShipmentLine
from src.modules.inventory.domain.shipment.error import (
    EmptyShipmentError,
    InvalidShipmentLineError,
    InvalidShipmentValueError,
    ShipmentLineConflictError,
    ShipmentLineNotFoundError,
    ShipmentStatusError,
    ShipmentTimeError,
    ShipmentVersionConflictError,
)
from src.modules.inventory.domain.shipment.order_snapshot import ShipmentOrderSnapshot
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_reservation.shipment_snapshot import (
    StockReservationShipmentSnapshot,
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
class Shipment:
    """План собственной отгрузки одного заказа со склада без изменения удержаний и физического запаса."""

    id: ShipmentIdVO
    order_ref: ShipmentOrderRefVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    status: ShipmentStatus
    lines: tuple[ShipmentLine, ...]
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: ShipmentIdVO,
        order_ref: ShipmentOrderRefVO,
        warehouse: WarehouseSnapshot,
        owner_id: StockOwnerIdVO,
        created_at: datetime,
    ) -> Self:
        """Создаёт пустой черновик версии 0 для активного склада и явно указанного заказа/владельца."""
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок склада отгрузки.")
        ShipmentConfirmationPolicy.ensure_warehouse(
            warehouse_id=warehouse.id, warehouse=warehouse
        )
        return cls.restore(
            identifier=identifier,
            order_ref=order_ref,
            warehouse_id=warehouse.id,
            owner_id=owner_id,
            status=ShipmentStatus.DRAFT,
            lines=(),
            created_at=created_at,
            updated_at=created_at,
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: ShipmentIdVO,
        order_ref: ShipmentOrderRefVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        status: ShipmentStatus,
        lines: tuple[ShipmentLine, ...],
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        """Восстанавливает полный собственный исторический состав без текущего заказа или удержаний."""
        shipment = cls(
            identifier,
            order_ref,
            warehouse_id,
            owner_id,
            status,
            lines,
            cls._normalize_time(created_at),
            cls._normalize_time(updated_at),
            version,
        )
        shipment._validate()
        return shipment

    def add_line(
        self,
        line: ShipmentLine,
        *,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        reservation: StockReservationShipmentSnapshot,
        updated_at: datetime,
    ) -> Self:
        """Добавляет проверенную строку только в черновик без увеличения удержания резерва."""
        normalized = self._prepare_transition(expected_version, updated_at)
        if not isinstance(line, ShipmentLine):
            raise InvalidShipmentLineError("Нужна дочерняя строка плана ShipmentLine.")
        line.ensure_compatible(inventory_item=inventory_item, reservation=reservation)
        ShipmentLinePolicy.ensure_available(
            warehouse_id=self.warehouse_id,
            owner_id=self.owner_id,
            as_of=normalized,
            reservation=reservation,
        )
        return self._changed(updated_at=normalized, lines=(*self.lines, line))

    def change_line_quantity(
        self,
        *,
        identifier: ShipmentLineIdVO,
        quantity: QuantityVO,
        uom: UomCodeVO,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        reservation: StockReservationShipmentSnapshot,
        updated_at: datetime,
    ) -> Self:
        """Меняет ввод количества, сохраняя идентичность, основание, товар, резерв и базовую единицу строки."""
        normalized = self._prepare_transition(expected_version, updated_at)
        previous = self._find_line(identifier)
        conversion = QuantityConversionSnapshotVO.create(
            quantity=quantity, uom=uom, base_uom=previous.base_uom
        )
        changed = ShipmentLine.restore(
            identifier=previous.id,
            source_ref=previous.source_ref,
            reservation_id=previous.reservation_id,
            inventory_item_id=previous.inventory_item_id,
            base_uom=previous.base_uom,
            planned_qty=conversion.to_base_quantity(),
            conversion=conversion,
        )
        changed.ensure_compatible(
            inventory_item=inventory_item, reservation=reservation
        )
        ShipmentLinePolicy.ensure_available(
            warehouse_id=self.warehouse_id,
            owner_id=self.owner_id,
            as_of=normalized,
            reservation=reservation,
        )
        return self._changed(
            updated_at=normalized,
            lines=tuple(
                changed if line.id == identifier else line for line in self.lines
            ),
        )

    def remove_line(
        self,
        identifier: ShipmentLineIdVO,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Удаляет строку черновика без текущих снимков, освобождения резерва и потери внешней истории."""
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
        warehouse: WarehouseSnapshot,
        order: ShipmentOrderSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        reservations: tuple[StockReservationShipmentSnapshot, ...],
        updated_at: datetime,
    ) -> Self:
        """Фиксирует план после проверки заказа и текущих удержаний без создания складского исполнения."""
        normalized = self._prepare_transition(expected_version, updated_at)
        ShipmentConfirmationPolicy.ensure_confirmable(
            order_ref=self.order_ref,
            warehouse_id=self.warehouse_id,
            owner_id=self.owner_id,
            lines=self.lines,
            warehouse=warehouse,
            order=order,
            inventory_items=inventory_items,
            reservations=reservations,
            as_of=normalized,
        )
        return self._changed(updated_at=normalized, status=ShipmentStatus.CONFIRMED)

    def cancel(self, *, expected_version: int, updated_at: datetime) -> Self:
        """Отменяет только черновик, сохраняя строки и не изменяя связанные резервы."""
        normalized = self._prepare_transition(expected_version, updated_at)
        return self._changed(updated_at=normalized, status=ShipmentStatus.CANCELLED)

    def _prepare_transition(
        self, expected_version: int, updated_at: datetime
    ) -> datetime:
        """Проверяет строгую версию до исторической арифметики, затем собственное состояние, черновик и время."""
        if (
            type(self.version) is not int
            or self.version < 0
            or type(expected_version) is not int
            or expected_version < 0
        ):
            raise InvalidShipmentValueError(
                "Текущая и ожидаемая версии должны быть целыми неотрицательными без bool."
            )
        if expected_version != self.version:
            raise ShipmentVersionConflictError(
                "Ожидаемая версия не совпадает с текущей версией отгрузки."
            )
        self._validate()
        if self.status is not ShipmentStatus.DRAFT:
            raise ShipmentStatusError(
                "Изменять, подтверждать и отменять можно только черновик отгрузки."
            )
        normalized = self._normalize_time(updated_at)
        if normalized < self.updated_at:
            raise ShipmentTimeError(
                "Время изменения не может быть раньше предыдущего изменения."
            )
        return normalized

    def _find_line(self, identifier: ShipmentLineIdVO) -> ShipmentLine:
        """Находит дочернюю строку данного плана без отдельного репозитория."""
        if not isinstance(identifier, ShipmentLineIdVO):
            raise InvalidShipmentLineError("Нужен типизированный ID строки отгрузки.")
        for line in self.lines:
            if line.id == identifier:
                return line
        raise ShipmentLineNotFoundError("Строка отсутствует в данном плане отгрузки.")

    def _changed(self, *, updated_at: datetime, **changes: object) -> Self:
        """Возвращает новый проверенный экземпляр версии +1 или исходный объект при равном содержимом."""
        candidate = replace(self, **changes)
        candidate._validate()
        if candidate == self:
            return self
        candidate = replace(candidate, updated_at=updated_at, version=self.version + 1)
        candidate._validate()
        return candidate

    def _validate(self) -> None:
        """Проверяет собственный состав, UTC-хронологию, уникальность строк/резервов и непустое подтверждение."""
        if (
            not isinstance(self.id, ShipmentIdVO)
            or not isinstance(self.order_ref, ShipmentOrderRefVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.status, ShipmentStatus)
            or not isinstance(self.lines, tuple)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidShipmentValueError(
                "Нужны типизированные значения, tuple строк и целая неотрицательная версия отгрузки."
            )
        created = self._normalize_time(self.created_at)
        updated = self._normalize_time(self.updated_at)
        if (
            self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or updated < created
        ):
            raise ShipmentTimeError(
                "Сохранённое время должно быть в UTC; изменение не раньше создания."
            )
        ids, reservations = set(), set()
        for line in self.lines:
            if not isinstance(line, ShipmentLine):
                raise InvalidShipmentLineError(
                    "Состав отгрузки содержит только ShipmentLine."
                )
            line.ensure_valid()
            if line.id in ids or line.reservation_id in reservations:
                raise ShipmentLineConflictError(
                    "ID строки и резерв не должны повторяться в отгрузке."
                )
            ids.add(line.id)
            reservations.add(line.reservation_id)
        if self.status is ShipmentStatus.CONFIRMED and not self.lines:
            raise EmptyShipmentError(
                "Подтверждённый план отгрузки не может быть пустым."
            )

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        """Нормализует явно переданное aware-время в UTC без обращения к системным часам."""
        if not isinstance(value, datetime):
            raise ShipmentTimeError("Нужен datetime с часовым поясом.")
        try:
            if value.utcoffset() is None:
                raise ShipmentTimeError("Время отгрузки должно содержать часовой пояс.")
            return value.astimezone(UTC)
        except (ValueError, OverflowError) as exc:
            raise ShipmentTimeError(
                "Время отгрузки невозможно представить в UTC."
            ) from exc
