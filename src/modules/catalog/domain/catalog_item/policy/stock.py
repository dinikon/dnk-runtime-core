"""Единое правило разрешения собственного и родительского наличия."""

from dataclasses import dataclass

from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)


@dataclass(frozen=True, slots=True)
class EffectiveStock:
    """Разрешённая спецификация и факт наследования количественного учёта."""

    specification: StockSpecificationVO
    inherited: bool


def resolve_stock(
    *, own: StockSpecificationVO, parent: StockSpecificationVO | None = None
) -> EffectiveStock:
    """Собственный учёт приоритетен; ручное наличие родителя детям не наследуется."""
    if own.manage_stock or parent is None or not parent.manage_stock:
        return EffectiveStock(own, False)
    return EffectiveStock(parent, True)
