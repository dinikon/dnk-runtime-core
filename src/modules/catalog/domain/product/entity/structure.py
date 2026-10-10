from dataclasses import dataclass
from typing import Self
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.catalog.domain.product.value_object.axis import VariationAxis
from src.modules.catalog.domain.product.value_object.selection import (
    VariationSelectionVO,
)


@dataclass(slots=True)
class SimpleProductStructure:
    """Внутренний компонент Product с единственной позицией."""

    variants: tuple[Variant, ...]
    axes: tuple[VariationAxis, ...] = ()
    default_selection: VariationSelectionVO | None = None

    @property
    def variant(self) -> Variant:
        """Возвращает единственную позицию проверенной Product структуры."""
        return self.variants[0]

    @classmethod
    def create(cls, variant: Variant) -> Self:
        """Собирает компонент; весь инвариант проверяет Product."""
        return cls((variant,))

    @classmethod
    def restore(
        cls,
        variants: tuple[Variant, ...],
        axes: tuple[VariationAxis, ...] = (),
        default_selection: VariationSelectionVO | None = None,
    ) -> Self:
        """Восстанавливает компонент без исправления данных."""
        return cls(variants, axes, default_selection)


@dataclass(slots=True)
class VariableProductStructure:
    """Внутренний компонент Product с осями и продаваемыми позициями."""

    axes: tuple[VariationAxis, ...]
    default_selection: VariationSelectionVO | None
    variants: tuple[Variant, ...]

    @classmethod
    def create(
        cls,
        axes: tuple[VariationAxis, ...],
        default_selection: VariationSelectionVO | None,
        variants: tuple[Variant, ...],
    ) -> Self:
        """Собирает структуру; согласованность и уникальность защищает Product."""
        return cls(axes, default_selection, variants)

    @classmethod
    def restore(
        cls,
        axes: tuple[VariationAxis, ...],
        default_selection: VariationSelectionVO | None,
        variants: tuple[Variant, ...],
    ) -> Self:
        """Восстанавливает компоненты без приведения некорректной структуры."""
        return cls(axes, default_selection, variants)
