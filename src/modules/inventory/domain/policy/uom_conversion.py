from decimal import (
    Context,
    DecimalException,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    MAX_EMAX,
    MIN_EMIN,
    Overflow,
    ROUND_HALF_EVEN,
    Underflow,
)

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    InvalidQuantityError,
    UomConversionError,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class UomConversionPolicy:
    """Точно пересчитывает количество по общим системным масштабам единиц."""

    @staticmethod
    def convert(
        *,
        quantity: QuantityVO,
        from_uom: UomCodeVO,
        to_uom: UomCodeVO,
    ) -> QuantityVO:
        """Пересчитывает внутри одной размерности без округления и внешнего Decimal context."""
        if not isinstance(quantity, QuantityVO):
            raise InvalidQuantityError("Для пересчёта требуется QuantityVO.")
        source = get_uom(from_uom)
        target = get_uom(to_uom)
        if source.dimension is not target.dimension:
            raise IncompatibleUomError("Единицы должны принадлежать одной размерности.")
        if source.code == target.code:
            return quantity
        # Системные масштабы — степени десяти; этого количества цифр достаточно
        # для точного произведения и деления без потери исходных разрядов.
        precision = sum(
            len(value.as_tuple().digits)
            for value in (
                quantity.value,
                source.factor_to_reference,
                target.factor_to_reference,
            )
        )
        context = Context(
            prec=precision,
            Emin=MIN_EMIN,
            Emax=MAX_EMAX,
            rounding=ROUND_HALF_EVEN,
            traps=[InvalidOperation, DivisionByZero, Overflow, Underflow, Inexact],
        )
        try:
            ratio = context.divide(
                source.factor_to_reference, target.factor_to_reference
            )
            result = context.multiply(quantity.value, ratio)
        except DecimalException as exc:
            raise UomConversionError(
                "Количество невозможно точно выразить в выбранной единице."
            ) from exc
        return QuantityVO(result)
