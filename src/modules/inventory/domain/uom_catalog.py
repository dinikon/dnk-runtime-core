from decimal import Decimal
from types import MappingProxyType

from src.modules.inventory.domain.error import InvalidUomCodeError, UnknownUomError
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.value_object.uom_definition import UomDefinitionVO
from src.modules.inventory.domain.value_object.uom_dimension import UomDimension

# Опорные единицы размерностей: PCS, KG, L, M и M2.
_UNITS: tuple[UomDefinitionVO, ...] = tuple(
    UomDefinitionVO(UomCodeVO(code), dimension, Decimal(factor))
    for dimension, entries in (
        (UomDimension.COUNT, (("PCS", "1"),)),
        (
            UomDimension.MASS,
            (
                ("UG", "0.000000001"),
                ("MG", "0.000001"),
                ("G", "0.001"),
                ("KG", "1"),
                ("CENTNER", "100"),
                ("T", "1000"),
            ),
        ),
        (UomDimension.VOLUME, (("ML", "0.001"), ("L", "1"), ("M3", "1000"))),
        (
            UomDimension.LENGTH,
            (
                ("UM", "0.000001"),
                ("MM", "0.001"),
                ("CM", "0.01"),
                ("DM", "0.1"),
                ("M", "1"),
                ("KM", "1000"),
            ),
        ),
        (
            UomDimension.AREA,
            (
                ("MM2", "0.000001"),
                ("CM2", "0.0001"),
                ("DM2", "0.01"),
                ("M2", "1"),
                ("HA", "10000"),
                ("KM2", "1000000"),
            ),
        ),
    )
    for code, factor in entries
)
_BY_CODE = MappingProxyType({unit.code: unit for unit in _UNITS})


def list_uoms() -> tuple[UomDefinitionVO, ...]:
    """Возвращает неизменяемый системный справочник, общий для всех товаров."""
    return _UNITS


def get_uom(code: UomCodeVO) -> UomDefinitionVO:
    """Находит системную единицу по точному коду или выбрасывает доменную ошибку."""
    if not isinstance(code, UomCodeVO):
        raise InvalidUomCodeError("Ожидался типизированный код единицы учёта.")
    unit = _BY_CODE.get(code)
    if unit is None:
        raise UnknownUomError("Единица отсутствует в системном справочнике.")
    return unit


def get_compatible_uoms(code: UomCodeVO) -> tuple[UomDefinitionVO, ...]:
    """Возвращает все системные единицы размерности выбранной базовой единицы."""
    dimension = get_uom(code).dimension
    return tuple(unit for unit in _UNITS if unit.dimension is dimension)
