from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.availability_pool.error import (
    InvalidAvailabilityPoolReservationSnapshotError,
)
from src.modules.inventory.domain.availability_pool.reservation_snapshot import (
    AvailabilityPoolReservationSnapshot,
)
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidStockReservationQuantityError,
    InvalidStockReservationValueError,
    StockReservationConsumptionExceededError,
    StockReservationExpirationError,
    StockReservationExpiredError,
    StockReservationItemMismatchError,
    StockReservationLimitExceededError,
    StockReservationReleaseExceededError,
    StockReservationStatusError,
    StockReservationTimeError,
    StockReservationUomMismatchError,
    StockReservationVersionConflictError,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockReservation:
    """Мягкое удержание под одну строку обязательства без изменения пула или физического запаса."""

    id: StockReservationIdVO
    source_ref: ReservationSourceVO
    pool_id: AvailabilityPoolIdVO
    key: AvailabilityPoolKeyVO
    base_uom: UomCodeVO
    requested_qty: QuantityVO
    reserved_qty: QuantityVO
    consumed_qty: QuantityVO
    status: StockReservationStatus
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: StockReservationIdVO,
        pool: AvailabilityPoolReservationSnapshot,
        inventory_item: InventoryItemStockSnapshot,
        source_ref: ReservationSourceVO,
        requested_qty: QuantityVO,
        created_at: datetime,
        expires_at: datetime | None = None,
    ) -> Self:
        """Создаёт ожидание версии 0 с нулевыми удержанием и погашением и проверенной привязкой к пулу."""
        if not isinstance(pool, AvailabilityPoolReservationSnapshot):
            raise InvalidAvailabilityPoolReservationSnapshotError(
                "Нужен снимок привязки к пулу, а не полный агрегат или его свободное количество."
            )
        pool.ensure_valid()
        reservation = cls.restore(
            identifier=identifier,
            source_ref=source_ref,
            pool_id=pool.id,
            key=pool.key,
            base_uom=pool.base_uom,
            requested_qty=requested_qty,
            reserved_qty=QuantityVO(Decimal(0)),
            consumed_qty=QuantityVO(Decimal(0)),
            status=StockReservationStatus.PENDING,
            expires_at=expires_at,
            created_at=created_at,
            updated_at=created_at,
            version=0,
        )
        reservation._ensure_item_compatible(inventory_item)
        return reservation

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockReservationIdVO,
        source_ref: ReservationSourceVO,
        pool_id: AvailabilityPoolIdVO,
        key: AvailabilityPoolKeyVO,
        base_uom: UomCodeVO,
        requested_qty: QuantityVO,
        reserved_qty: QuantityVO,
        consumed_qty: QuantityVO,
        status: StockReservationStatus,
        expires_at: datetime | None,
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        """Восстанавливает собственную историю, нормализуя время в UTC без текущих снимков и часов."""
        reservation = cls(
            identifier,
            source_ref,
            pool_id,
            key,
            base_uom,
            requested_qty,
            reserved_qty,
            consumed_qty,
            status,
            cls._normalize_time(expires_at) if expires_at is not None else None,
            cls._normalize_time(created_at),
            cls._normalize_time(updated_at),
            version,
        )
        reservation._validate()
        return reservation

    def add_reserved(
        self,
        quantity: QuantityVO,
        *,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        updated_at: datetime,
    ) -> Self:
        """Регистрирует увеличение собственного удержания до лимита без проверки общего свободного запаса."""
        normalized = self._prepare_transition(expected_version, updated_at)
        if self.expires_at is not None and normalized >= self.expires_at:
            raise StockReservationExpiredError(
                "Срок действия резерва истёк; увеличение удержания запрещено."
            )
        self._ensure_item_compatible(inventory_item)
        self._ensure_positive_quantity(quantity, inventory_item.quantity_rules)
        reserved = QuantityArithmeticPolicy.add(self.reserved_qty, quantity)
        accounted = QuantityArithmeticPolicy.add(reserved, self.consumed_qty)
        if accounted.value > self.requested_qty.value:
            raise StockReservationLimitExceededError(
                "Удержание вместе с погашением не может превышать запрос."
            )
        status = self._active_status(reserved, self.consumed_qty)
        return self._changed(
            reserved_qty=reserved, status=status, updated_at=normalized
        )

    def release(
        self,
        quantity: QuantityVO,
        *,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        updated_at: datetime,
    ) -> Self:
        """Освобождает часть собственного удержания, разрешая операцию и после окончания срока."""
        normalized = self._prepare_transition(expected_version, updated_at)
        self._ensure_item_compatible(inventory_item)
        self._ensure_positive_quantity(quantity, inventory_item.quantity_rules)
        if quantity.value > self.reserved_qty.value:
            raise StockReservationReleaseExceededError(
                "Нельзя освободить больше удерживаемого обязательством количества."
            )
        reserved = QuantityArithmeticPolicy.subtract(self.reserved_qty, quantity)
        status = (
            StockReservationStatus.RELEASED
            if reserved.value.is_zero()
            else self._active_status(reserved, self.consumed_qty)
        )
        return self._changed(
            reserved_qty=reserved, status=status, updated_at=normalized
        )

    def consume(
        self,
        quantity: QuantityVO,
        *,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        consumed_at: datetime,
        updated_at: datetime,
    ) -> Self:
        """Переносит текущее удержание в накопленное использование без подтверждения складского исполнения."""
        normalized = self._prepare_transition(expected_version, updated_at)
        occurred = self._normalize_time(consumed_at)
        if occurred < self.created_at or occurred > normalized:
            raise StockReservationTimeError(
                "Использование должно быть не раньше создания и не позже регистрации."
            )
        if self.expires_at is not None and occurred >= self.expires_at:
            raise StockReservationExpiredError(
                "Факт использования должен произойти до срока действия резерва."
            )
        self._ensure_item_compatible(inventory_item)
        self._ensure_positive_quantity(quantity, inventory_item.quantity_rules)
        if quantity.value > self.reserved_qty.value:
            raise StockReservationConsumptionExceededError(
                "Нельзя погасить больше текущего удержания обязательства."
            )
        reserved = QuantityArithmeticPolicy.subtract(self.reserved_qty, quantity)
        consumed = QuantityArithmeticPolicy.add(self.consumed_qty, quantity)
        return self._changed(
            reserved_qty=reserved,
            consumed_qty=consumed,
            status=self._active_status(reserved, consumed),
            updated_at=normalized,
        )

    def release_all(self, *, expected_version: int, updated_at: datetime) -> Self:
        """Закрывает весь резерв, включая ожидание без удержания, без текущего физического контекста."""
        normalized = self._prepare_transition(expected_version, updated_at)
        return self._changed(
            reserved_qty=QuantityVO(Decimal(0)),
            status=StockReservationStatus.RELEASED,
            updated_at=normalized,
        )

    def expire(self, *, expected_version: int, updated_at: datetime) -> Self:
        """Явно закрывает резерв в момент срока или позже, не обращаясь к системным часам."""
        normalized = self._prepare_transition(expected_version, updated_at)
        if self.expires_at is None or normalized < self.expires_at:
            raise StockReservationExpirationError(
                "Для завершения по сроку нужна заданная и уже наступившая граница."
            )
        return self._changed(
            reserved_qty=QuantityVO(Decimal(0)),
            status=StockReservationStatus.EXPIRED,
            updated_at=normalized,
        )

    def _prepare_transition(
        self, expected_version: int, updated_at: datetime
    ) -> datetime:
        """Проверяет версии до арифметики инварианта, затем собственный состав, статус и время."""
        if (
            type(self.version) is not int
            or self.version < 0
            or type(expected_version) is not int
            or expected_version < 0
        ):
            raise InvalidStockReservationValueError(
                "Ожидаемая версия должна быть целой неотрицательной без bool."
            )
        if expected_version != self.version:
            raise StockReservationVersionConflictError(
                "Ожидаемая версия не совпадает с текущей версией резерва."
            )
        self._validate()
        if self.status.is_terminal:
            raise StockReservationStatusError(
                "Закрытый резерв не изменяется; для нового удержания создайте новый объект."
            )
        normalized = self._normalize_time(updated_at)
        if normalized < self.updated_at:
            raise StockReservationTimeError(
                "Время изменения не может быть раньше предыдущего изменения."
            )
        return normalized

    def _ensure_item_compatible(
        self, inventory_item: InventoryItemStockSnapshot
    ) -> None:
        """Требует тот же товар, прежнюю единицу и кратность всех количеств текущему шагу."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен учётный снимок товара обязательства."
            )
        inventory_item.ensure_valid()
        if inventory_item.inventory_item_id != self.key.inventory_item_id:
            raise StockReservationItemMismatchError(
                "Настройки относятся к другому товару."
            )
        if inventory_item.base_uom != self.base_uom:
            raise StockReservationUomMismatchError(
                "Базовая единица обязательства не может быть заменена."
            )
        for quantity in (self.requested_qty, self.reserved_qty, self.consumed_qty):
            QuantityValidationPolicy.validate(
                quantity=quantity, rules=inventory_item.quantity_rules
            )

    def _changed(
        self,
        *,
        reserved_qty: QuantityVO,
        status: StockReservationStatus,
        updated_at: datetime,
        consumed_qty: QuantityVO | None = None,
    ) -> Self:
        """Возвращает новый проверенный экземпляр одной следующей версии с прежним основанием и областью."""
        reservation = replace(
            self,
            reserved_qty=reserved_qty,
            consumed_qty=self.consumed_qty if consumed_qty is None else consumed_qty,
            status=status,
            updated_at=updated_at,
            version=self.version + 1,
        )
        reservation._validate()
        return reservation

    def _validate(self) -> None:
        """Проверяет собственный состав, сумму удержания и погашения, статусы и UTC-хронологию."""
        if (
            not isinstance(self.id, StockReservationIdVO)
            or not isinstance(self.source_ref, ReservationSourceVO)
            or not isinstance(self.pool_id, AvailabilityPoolIdVO)
            or not isinstance(self.key, AvailabilityPoolKeyVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.requested_qty, QuantityVO)
            or not isinstance(self.reserved_qty, QuantityVO)
            or not isinstance(self.consumed_qty, QuantityVO)
            or not isinstance(self.status, StockReservationStatus)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidStockReservationValueError(
                "Нужны типизированные значения и целая неотрицательная версия резерва."
            )
        get_uom(self.base_uom)
        if self.requested_qty.value.is_zero():
            raise InvalidStockReservationQuantityError(
                "Запрошенное количество должно быть положительным."
            )
        accounted = QuantityArithmeticPolicy.add(self.reserved_qty, self.consumed_qty)
        if accounted.value > self.requested_qty.value:
            raise StockReservationLimitExceededError(
                "Удержание вместе с погашением не может превышать запрос."
            )
        created = self._normalize_time(self.created_at)
        updated = self._normalize_time(self.updated_at)
        expires = (
            self._normalize_time(self.expires_at)
            if self.expires_at is not None
            else None
        )
        if (
            self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or updated < created
            or (
                expires is not None
                and (self.expires_at.utcoffset() != timedelta(0) or expires <= created)
            )
        ):
            raise StockReservationTimeError(
                "Нужны даты в UTC: изменение не раньше создания, срок строго позже создания."
            )
        zero = self.reserved_qty.value.is_zero()
        full = self.reserved_qty == self.requested_qty
        consumed_zero = self.consumed_qty.value.is_zero()
        consumed_full = self.consumed_qty == self.requested_qty
        if (
            (
                self.status is StockReservationStatus.PENDING
                and (not zero or not consumed_zero)
            )
            or (
                self.status is StockReservationStatus.PARTIALLY_RESERVED
                and (zero or full or not consumed_zero)
            )
            or (
                self.status is StockReservationStatus.RESERVED
                and (not full or not consumed_zero)
            )
            or (
                self.status is StockReservationStatus.PARTIALLY_CONSUMED
                and (consumed_zero or consumed_full)
            )
            or (
                self.status is StockReservationStatus.CONSUMED
                and (not consumed_full or not zero)
            )
            or (
                self.status
                in (StockReservationStatus.RELEASED, StockReservationStatus.EXPIRED)
                and (not zero or consumed_full)
            )
        ):
            raise StockReservationStatusError(
                "Статус не соответствует удерживаемому и погашенному количествам."
            )
        if self.status is StockReservationStatus.EXPIRED and (
            expires is None or updated < expires
        ):
            raise StockReservationExpirationError(
                "EXPIRED требует срок и время закрытия не раньше срока."
            )

    def _active_status(
        self, reserved: QuantityVO, consumed: QuantityVO
    ) -> StockReservationStatus:
        """Выбирает открытый статус или полное погашение по проверяемым количествам."""
        if consumed == self.requested_qty:
            return StockReservationStatus.CONSUMED
        if not consumed.value.is_zero():
            return StockReservationStatus.PARTIALLY_CONSUMED
        if reserved == self.requested_qty:
            return StockReservationStatus.RESERVED
        if not reserved.value.is_zero():
            return StockReservationStatus.PARTIALLY_RESERVED
        return StockReservationStatus.PENDING

    @staticmethod
    def _ensure_positive_quantity(quantity: QuantityVO, rules: QuantityRulesVO) -> None:
        """Требует положительный QuantityVO, точно кратный шагу товара."""
        QuantityValidationPolicy.validate(quantity=quantity, rules=rules)
        if quantity.value.is_zero():
            raise InvalidStockReservationQuantityError(
                "Количество изменения удержания должно быть положительным."
            )

    @staticmethod
    def _normalize_time(value: datetime) -> datetime:
        """Нормализует явный aware datetime в UTC без чтения системного времени."""
        if not isinstance(value, datetime):
            raise StockReservationTimeError(
                "Время резерва должно быть datetime с часовым поясом."
            )
        try:
            if value.utcoffset() is None:
                raise StockReservationTimeError(
                    "Время резерва должно содержать часовой пояс."
                )
            return value.astimezone(UTC)
        except (ValueError, OverflowError) as exc:
            raise StockReservationTimeError(
                "Время резерва невозможно представить в UTC."
            ) from exc
