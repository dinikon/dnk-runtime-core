from dataclasses import dataclass

from src.modules.inventory.domain.value_object.uom_dimension import UomDimension


@dataclass(frozen=True, slots=True)
class ListUomsItemDTO:
    """Передаёт код единицы и её размерность для выбора базовой единицы."""

    code: str
    dimension: UomDimension


@dataclass(frozen=True, slots=True)
class ListUomsResultDTO:
    """Передаёт полный набор разрешённых системных единиц учёта."""

    items: tuple[ListUomsItemDTO, ...]
