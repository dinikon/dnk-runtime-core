from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from src.modules.catalog.domain.error import InvalidCatalogValueError


class WeightUnit(StrEnum):
    """Единицы массы, принимаемые Catalog."""

    G = "g"
    KG = "kg"


class LengthUnit(StrEnum):
    """Единицы линейных размеров, принимаемые Catalog."""

    CM = "cm"
    M = "m"


def canonical_value(value: Decimal, power: int) -> Decimal:
    """Переводит Decimal в каноническую единицу без округления контекстом."""
    parts = value.as_tuple()
    return Decimal((parts.sign, parts.digits, parts.exponent + power))


def ensure_measurement(value: Decimal, power: int) -> None:
    """Проверяет неотрицательное конечное значение с точностью до микродоли."""
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise InvalidCatalogValueError(
            "Измерение должно быть конечным неотрицательным Decimal."
        )
    parts = value.as_tuple()
    digits = list(parts.digits)
    exponent = parts.exponent + power
    while digits and digits[-1] == 0:
        digits.pop()
        exponent += 1
    if digits and exponent < -6:
        raise InvalidCatalogValueError(
            "Измерение слишком точное для канонической единицы."
        )


@dataclass(frozen=True, slots=True)
class WeightVO:
    """Масса с собственной единицей и точным переводом в граммы."""

    value: Decimal
    unit: WeightUnit

    def __post_init__(self) -> None:
        """Проверяет единицу и точность массы в граммах."""
        if not isinstance(self.unit, WeightUnit):
            raise InvalidCatalogValueError("Вес требует единицу g или kg.")
        ensure_measurement(self.value, 3 if self.unit == WeightUnit.KG else 0)

    def in_grams(self) -> Decimal:
        """Возвращает массу в граммах без изменения собственного значения."""
        return canonical_value(self.value, 3 if self.unit == WeightUnit.KG else 0)


@dataclass(frozen=True, slots=True)
class LengthVO:
    """Линейный размер со своей единицей и точным переводом в миллиметры."""

    value: Decimal
    unit: LengthUnit

    def __post_init__(self) -> None:
        """Проверяет единицу и точность размера в миллиметрах."""
        if not isinstance(self.unit, LengthUnit):
            raise InvalidCatalogValueError("Размер требует единицу cm или m.")
        ensure_measurement(self.value, 3 if self.unit == LengthUnit.M else 1)

    def in_millimeters(self) -> Decimal:
        """Возвращает размер в миллиметрах без округления."""
        return canonical_value(self.value, 3 if self.unit == LengthUnit.M else 1)


@dataclass(frozen=True, slots=True)
class DimensionsVO:
    """Независимые необязательные размеры с собственными единицами."""

    length: LengthVO | None = None
    width: LengthVO | None = None
    height: LengthVO | None = None

    def __post_init__(self) -> None:
        """Запрещает передавать число без единицы вместо размера."""
        if any(
            v is not None and not isinstance(v, LengthVO)
            for v in (self.length, self.width, self.height)
        ):
            raise InvalidCatalogValueError("Каждый размер требует значение и единицу.")
