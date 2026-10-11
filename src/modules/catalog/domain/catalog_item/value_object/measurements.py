from dataclasses import dataclass
from decimal import Decimal
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class DimensionsVO:
    """Полные размеры в миллиметрах, переопределяемые одним значением."""

    length: Decimal
    width: Decimal
    height: Decimal

    def __post_init__(self) -> None:
        """Проверяет конечные неотрицательные размеры."""
        if any(
            not isinstance(v, Decimal)
            or not v.is_finite()
            or v < 0
            or v.as_tuple().exponent < -6
            for v in (self.length, self.width, self.height)
        ):
            raise InvalidCatalogValueError(
                "Размеры должны быть неотрицательными Decimal с точностью до 6 знаков."
            )
