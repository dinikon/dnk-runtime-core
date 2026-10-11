from dataclasses import dataclass
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.catalog_item.value_object.axis import VariationAxis


@dataclass(frozen=True, slots=True)
class VariantStructureInput:
    """Позиция структурной команды: существующий ID либо новый серверный ID."""

    item_id: CatalogItemIdVO | None
    selection: VariationSelectionVO


@dataclass(frozen=True, slots=True)
class VariableStructureInput:
    """Полный состав осей, вариантов и default для одной операции семьи."""

    axes: tuple[VariationAxis, ...]
    variants: tuple[VariantStructureInput, ...]
    default_selection: VariationSelectionVO | None = None
