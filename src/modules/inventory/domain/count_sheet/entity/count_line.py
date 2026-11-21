from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountLineError,
    CountSheetTimeError,
)
from src.modules.inventory.domain.count_sheet.time import normalize_count_sheet_time
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.count_sheet.value_object.line_origin import (
    CountLineOrigin,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class CountLine:
    """Дочерняя строка с неизменными учётными данными и опциональным фактом пересчёта в базовой единице."""

    id: CountLineIdVO
    origin: CountLineOrigin
    position_id: StockPositionIdVO | None
    dimensions: StockDimensionsVO
    base_uom: UomCodeVO
    expected_qty: QuantityVO
    position_version: int | None
    counted_qty: QuantityVO | None
    counted_at: datetime | None

    @classmethod
    def create(
        cls, *, identifier: CountLineIdVO, position: StockPositionCountingSnapshot
    ) -> Self:
        """Копирует исходную позицию без установки нуля вместо отсутствующего результата пересчёта."""
        if not isinstance(position, StockPositionCountingSnapshot):
            raise InvalidCountLineError("Нужен снимок позиции учётного основания.")
        position.ensure_valid()
        return cls.restore(
            identifier=identifier,
            origin=CountLineOrigin.BASELINE,
            position_id=position.id,
            dimensions=position.dimensions,
            base_uom=position.base_uom,
            expected_qty=position.on_hand_qty,
            position_version=position.version,
            counted_qty=None,
            counted_at=None,
        )

    @classmethod
    def create_found(
        cls,
        *,
        identifier: CountLineIdVO,
        dimensions: StockDimensionsVO,
        base_uom: UomCodeVO,
    ) -> Self:
        """Создаёт непосчитанную найденную строку с нулевым учётом без фиктивного ID или версии позиции."""
        return cls.restore(
            identifier=identifier,
            origin=CountLineOrigin.FOUND,
            position_id=None,
            position_version=None,
            dimensions=dimensions,
            base_uom=base_uom,
            expected_qty=QuantityVO(Decimal(0)),
            counted_qty=None,
            counted_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: CountLineIdVO,
        origin: CountLineOrigin,
        position_id: StockPositionIdVO | None,
        dimensions: StockDimensionsVO,
        base_uom: UomCodeVO,
        expected_qty: QuantityVO,
        position_version: int | None,
        counted_qty: QuantityVO | None,
        counted_at: datetime | None,
    ) -> Self:
        """Восстанавливает собственную историю строки без текущих правил товара или полного основания."""
        line = cls(
            identifier,
            origin,
            position_id,
            dimensions,
            base_uom,
            expected_qty,
            position_version,
            counted_qty,
            None if counted_at is None else normalize_count_sheet_time(counted_at),
        )
        line.ensure_valid()
        return line

    def baseline_position_snapshot(self) -> StockPositionCountingSnapshot | None:
        """Возвращает исходную учётную позицию либо None для найденных измерений без позиции."""
        if self.origin is CountLineOrigin.FOUND:
            return None
        return StockPositionCountingSnapshot(
            self.position_id,
            self.dimensions,
            self.base_uom,
            self.expected_qty,
            self.position_version,
        )

    def ensure_valid(self) -> None:
        """Проверяет собственные поля, согласованность пары факта/момента и поштучность SERIAL."""
        if not isinstance(self.id, CountLineIdVO) or not isinstance(
            self.origin, CountLineOrigin
        ):
            raise InvalidCountLineError(
                "Нужны CountLineIdVO и типизированный источник строки."
            )
        if self.origin is CountLineOrigin.BASELINE:
            StockPositionCountingSnapshot(
                self.position_id,
                self.dimensions,
                self.base_uom,
                self.expected_qty,
                self.position_version,
            ).ensure_valid()
        else:
            if (
                self.position_id is not None
                or self.position_version is not None
                or not isinstance(self.dimensions, StockDimensionsVO)
                or not isinstance(self.base_uom, UomCodeVO)
                or not isinstance(self.expected_qty, QuantityVO)
                or not self.expected_qty.value.is_zero()
            ):
                raise InvalidCountLineError(
                    "FOUND требует измерения, единицу, нулевой учёт и отсутствие ID/версии позиции."
                )
            get_uom(self.base_uom)
            if self.dimensions.serial_id is not None and self.base_uom != UomCodeVO(
                "PCS"
            ):
                raise InvalidCountLineError("Конкретный найденный SERIAL требует PCS.")
        if (self.counted_qty is None) != (self.counted_at is None):
            raise InvalidCountLineError(
                "Количество и момент пересчёта заполняются вместе."
            )
        if self.counted_qty is not None:
            if not isinstance(self.counted_qty, QuantityVO):
                raise InvalidCountLineError(
                    "Нужно неотрицательное фактическое QuantityVO."
                )
            normalize_count_sheet_time(self.counted_at)
            if self.counted_at.utcoffset() != timedelta(0):
                raise CountSheetTimeError("Момент пересчёта должен храниться в UTC.")
            if (
                self.dimensions.serial_id is not None
                and self.counted_qty.value not in (Decimal(0), Decimal(1))
            ):
                raise InvalidCountLineError(
                    "Факт конкретного SERIAL может быть только 0 или 1 PCS."
                )

    def record_count(self, *, quantity: QuantityVO, counted_at: datetime) -> Self:
        """Возвращает новый локальный результат без изменения учётных полей, запрещая убывание момента пересчёта."""
        self.ensure_valid()
        normalized = normalize_count_sheet_time(counted_at)
        if self.counted_at is not None and normalized < self.counted_at:
            raise CountSheetTimeError(
                "Момент повторного пересчёта строки не может убывать."
            )
        changed = replace(self, counted_qty=quantity, counted_at=normalized)
        changed.ensure_valid()
        return changed

    @property
    def discrepancy(self) -> StockDeltaVO | None:
        """Вычисляет точную знаковую разность без хранения дублирующей дельты и зависимости от Decimal context."""
        self.ensure_valid()
        if self.counted_qty is None:
            return None
        if self.counted_qty.value >= self.expected_qty.value:
            return StockDeltaVO(
                QuantityArithmeticPolicy.subtract(
                    self.counted_qty, self.expected_qty
                ).value
            )
        return StockDeltaVO(
            QuantityArithmeticPolicy.subtract(
                self.expected_qty, self.counted_qty
            ).value.copy_negate()
        )
