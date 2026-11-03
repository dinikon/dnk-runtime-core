from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    QuantityConversionMismatchError,
)
from src.modules.inventory.domain.policy.uom_conversion import UomConversionPolicy
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockLedgerEntryError,
    ZeroStockLedgerDeltaError,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockLedgerEntry:
    """Неизменяемая дочерняя запись проведения с дельтой в базовой единице."""

    id: StockLedgerEntryIdVO
    position_id: StockPositionIdVO
    quantity_delta: StockDeltaVO
    base_uom: UomCodeVO
    conversion: QuantityConversionSnapshotVO

    @classmethod
    def create(
        cls,
        *,
        identifier: StockLedgerEntryIdVO,
        position_id: StockPositionIdVO,
        quantity_delta: StockDeltaVO,
        base_uom: UomCodeVO,
        conversion: QuantityConversionSnapshotVO,
    ) -> Self:
        """Создаёт запись с пересчётом, соответствующим текущему системному справочнику."""
        entry = cls.restore(
            identifier=identifier,
            position_id=position_id,
            quantity_delta=quantity_delta,
            base_uom=base_uom,
            conversion=conversion,
        )
        entry.ensure_current_conversion()
        return entry

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockLedgerEntryIdVO,
        position_id: StockPositionIdVO,
        quantity_delta: StockDeltaVO,
        base_uom: UomCodeVO,
        conversion: QuantityConversionSnapshotVO,
    ) -> Self:
        """Восстанавливает запись, проверяя сохранённую связь величин без замены коэффициента."""
        entry = cls(identifier, position_id, quantity_delta, base_uom, conversion)
        entry.ensure_valid()
        return entry

    def ensure_current_conversion(self) -> None:
        """Проверяет системный коэффициент при новом обычном проведении без изменения истории."""
        self.ensure_valid()
        expected_factor = UomConversionPolicy.convert(
            quantity=QuantityVO(Decimal(1)),
            from_uom=self.conversion.uom,
            to_uom=self.base_uom,
        )
        if self.conversion.factor_to_base != expected_factor.value:
            raise QuantityConversionMismatchError(
                "Коэффициент новой записи не соответствует системному пересчёту."
            )

    def ensure_valid(self) -> None:
        """Проверяет собственный состав, ненулевую дельту и точность исторического пересчёта."""
        if (
            not isinstance(self.id, StockLedgerEntryIdVO)
            or not isinstance(self.position_id, StockPositionIdVO)
            or not isinstance(self.quantity_delta, StockDeltaVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.conversion, QuantityConversionSnapshotVO)
        ):
            raise InvalidStockLedgerEntryError(
                "Нужны типизированные значения записи журнала."
            )
        base = get_uom(self.base_uom)
        source = get_uom(self.conversion.uom)
        if base.dimension is not source.dimension:
            raise IncompatibleUomError(
                "Исходная и базовая единицы должны иметь одну размерность."
            )
        if self.quantity_delta.value.is_zero():
            raise ZeroStockLedgerDeltaError("Нулевая дельта не создаёт запись журнала.")
        if (
            self.conversion.to_base_quantity().value
            != self.quantity_delta.value.copy_abs()
        ):
            raise QuantityConversionMismatchError(
                "Исходное количество с коэффициентом не равно модулю дельты."
            )
