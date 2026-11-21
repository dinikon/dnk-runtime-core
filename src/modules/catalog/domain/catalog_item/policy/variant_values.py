from src.modules.catalog.domain.catalog_item.policy.stock import resolve_stock
from dataclasses import dataclass, replace
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


@dataclass(frozen=True, slots=True)
class CatalogVariantEffectiveValues:
    """Эффективные значения и владельцы источников без копирования в хранение."""

    values: CatalogItemValuesSnapshot
    title_source_id: CatalogItemIdVO | None
    body_source_id: CatalogItemIdVO | None
    gallery_source_id: CatalogItemIdVO | None
    weight_source_id: CatalogItemIdVO | None
    dimensions_source_id: CatalogItemIdVO | None
    stock_source_id: CatalogItemIdVO


def effective_variant(
    parent: CatalogItemValuesSnapshot, own: CatalogItemValuesSnapshot, locale: str
) -> CatalogVariantEffectiveValues:
    """Разрешает независимое наследование строго внутри одной locale."""
    if own.parent_id != parent.id:
        raise InvalidCatalogValueError("Вариант принадлежит другому родителю.")
    base = parent.translations.get(locale, {})
    overrides = own.translations.get(locale, {})
    values = {**base, **overrides}
    gallery = (
        own.galleries.get(locale)
        if locale in own.galleries
        else parent.galleries.get(locale)
    )
    resolved_stock = resolve_stock(own=own.stock, parent=parent.stock)
    inherits_stock = resolved_stock.inherited
    stock = resolved_stock.specification
    return CatalogVariantEffectiveValues(
        replace(
            own,
            translations={locale: values} if values else {},
            galleries={locale: gallery} if gallery is not None else {},
            stock=stock,
            weight=own.weight if own.weight is not None else parent.weight,
            dimensions=(
                own.dimensions if own.dimensions is not None else parent.dimensions
            ),
            status=(
                own.status
                if parent.status is CatalogItemStatus.ACTIVE
                else parent.status
            ),
        ),
        own.id if "title" in overrides else parent.id if "title" in base else None,
        own.id if "body" in overrides else parent.id if "body" in base else None,
        (
            own.id
            if locale in own.galleries
            else parent.id if gallery is not None else None
        ),
        (
            own.id
            if own.weight is not None
            else parent.id if parent.weight is not None else None
        ),
        (
            own.id
            if own.dimensions is not None
            else parent.id if parent.dimensions is not None else None
        ),
        parent.id if inherits_stock else own.id,
    )
