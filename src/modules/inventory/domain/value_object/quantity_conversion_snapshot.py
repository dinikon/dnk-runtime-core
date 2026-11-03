from dataclasses import dataclass
from decimal import (
    Context,
    Decimal,
    DecimalException,
    Inexact,
    InvalidOperation,
    MAX_EMAX,
    MIN_EMIN,
    Overflow,
    Underflow,
)
from typing import Self

from src.modules.inventory.domain.error import InvalidQuantityConversionError
from src.modules.inventory.domain.policy.uom_conversion import UomConversionPolicy
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class QuantityConversionSnapshotVO:
    """Сохраняет положительное исходное количество, его единицу и исторический коэффициент."""

    quantity: QuantityVO
    uom: UomCodeVO
    factor_to_base: Decimal

    def __post_init__(self) -> None:
        """Требует типизированные значения и конечный положительный коэффициент без округления."""
        if (
            not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.uom, UomCodeVO)
            or not isinstance(self.factor_to_base, Decimal)
            or not self.factor_to_base.is_finite()
            or self.factor_to_base <= 0
        ):
            raise InvalidQuantityConversionError(
                "Нужны положительное QuantityVO, известная единица и конечный положительный Decimal-коэффициент."
            )
        get_uom(self.uom)

    @classmethod
    def create(
        cls, *, quantity: QuantityVO, uom: UomCodeVO, base_uom: UomCodeVO
    ) -> Self:
        """Фиксирует системный коэффициент и проверяет точную представимость пересчёта сейчас."""
        factor = UomConversionPolicy.convert(
            quantity=QuantityVO(Decimal(1)), from_uom=uom, to_uom=base_uom
        )
        UomConversionPolicy.convert(quantity=quantity, from_uom=uom, to_uom=base_uom)
        return cls(quantity, uom, factor.value)

    def to_base_quantity(self) -> QuantityVO:
        """Применяет сохранённый коэффициент без обращения к текущим масштабам единиц."""
        context = Context(
            prec=len(self.quantity.value.as_tuple().digits)
            + len(self.factor_to_base.as_tuple().digits),
            Emin=MIN_EMIN,
            Emax=MAX_EMAX,
            traps=[InvalidOperation, Overflow, Underflow, Inexact],
        )
        try:
            result = context.multiply(self.quantity.value, self.factor_to_base)
        except DecimalException as exc:
            raise InvalidQuantityConversionError(
                "Сохранённый пересчёт невозможно представить точно."
            ) from exc
        return QuantityVO(result)
