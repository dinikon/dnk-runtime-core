from dataclasses import dataclass
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.product.value_object.axis import VariationAxis
from src.modules.catalog.domain.product.value_object.selection import (
    VariationSelectionVO,
)


@dataclass(frozen=True, slots=True)
class VariantStructureInput:
    """Позиция редактора структуры; новый ID генерирует сервер."""

    selection: VariationSelectionVO
    virtual: bool = False
    variant_id: VariantIdVO | None = None


@dataclass(frozen=True, slots=True)
class SimpleStructureInput:
    """Полная входная структура SIMPLE для явного перехода вида."""

    variant: VariantStructureInput


@dataclass(frozen=True, slots=True)
class VariableStructureInput:
    """Полная входная структура VARIABLE без универсального dict."""

    axes: tuple[VariationAxis, ...]
    default_selection: VariationSelectionVO | None
    variants: tuple[VariantStructureInput, ...]
