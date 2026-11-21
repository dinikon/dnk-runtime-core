from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.error import InvalidUomDefinitionError
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.value_object.uom_dimension import UomDimension


@dataclass(frozen=True, slots=True)
class UomDefinitionVO:
    """Системная единица и её масштаб относительно опорной единицы размерности."""

    code: UomCodeVO
    dimension: UomDimension
    factor_to_reference: Decimal

    def __post_init__(self) -> None:
        """Проверяет типы и конечный положительный коэффициент единицы."""
        if (
            not isinstance(self.code, UomCodeVO)
            or not isinstance(self.dimension, UomDimension)
            or not isinstance(self.factor_to_reference, Decimal)
            or not self.factor_to_reference.is_finite()
            or self.factor_to_reference <= 0
        ):
            raise InvalidUomDefinitionError(
                "Нужны код, размерность и положительный Decimal масштаба."
            )
