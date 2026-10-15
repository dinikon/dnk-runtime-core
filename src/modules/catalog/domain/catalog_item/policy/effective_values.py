from datetime import datetime
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
    EffectiveCatalogItemValues,
    ValueOrigin,
)
from src.modules.catalog.domain.catalog_item.value_object.override import (
    OverrideMode,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import StockStatus
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
    WeightVO,
    LengthVO,
)
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogFamilySummary,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute import (
    EnumAttributeAssignmentVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


class CatalogItemEffectiveValuesPolicy:
    """Одна чистая политика наследования для Domain и read projections."""

    @staticmethod
    def resolve(
        item: CatalogItemValuesSnapshot,
        parent: CatalogItemValuesSnapshot | None,
        locale: str,
        as_of: datetime,
    ) -> EffectiveCatalogItemValues:
        """Разрешает значения только своего родителя и той же locale."""
        if item.kind == CatalogItemKind.VARIANT and (
            parent is None
            or parent.id != item.parent_id
            or parent.kind != CatalogItemKind.VARIABLE
        ):
            raise InvalidCatalogValueError("Для варианта нужен снимок своего VARIABLE.")
        origins: dict[str, ValueOrigin] = {}

        def measurement[T: (WeightVO, LengthVO)](
            name: str, own: T | None, inherited: T | None
        ) -> T | None:
            """Наследует отсутствующее измерение вместе с единицей, сохраняя собственный ноль."""
            value = own if own is not None else inherited
            source = (
                "item"
                if own is not None
                else "parent" if inherited is not None else "unknown"
            )
            origins[name] = ValueOrigin(
                source,
                (
                    item.id
                    if own is not None
                    else parent.id if parent and inherited is not None else None
                ),
            )
            return value

        content: dict[str, str] = {}
        own_content = item.translations.get(locale, {})
        inherited_content = parent.translations.get(locale, {}) if parent else {}
        for code in ("name", "desc", "short_desc"):
            own = own_content.get(code)
            inherited = inherited_content.get(code)
            value = own if own is not None else inherited
            origin_id = item.id if own is not None else parent.id if parent else None
            origins[code] = ValueOrigin(
                (
                    "item"
                    if own is not None
                    else "parent" if inherited is not None else "unknown"
                ),
                origin_id,
                locale,
            )
            if value is not None and value.mode == OverrideMode.SET:
                content[code] = value.value
        virtual = item.virtual
        price = item.price
        origins["virtual"] = ValueOrigin("item", item.id)
        origins["price"] = ValueOrigin(
            "item" if price is not None else "unknown",
            item.id if price is not None else None,
        )
        weight = measurement("weight", item.weight, parent.weight if parent else None)
        own_dimensions = item.dimensions or DimensionsVO()
        parent_dimensions = (
            parent.dimensions if parent and parent.dimensions else DimensionsVO()
        )
        sizes = tuple(
            measurement(
                f"dimensions.{name}",
                getattr(own_dimensions, name),
                getattr(parent_dimensions, name),
            )
            for name in ("length", "width", "height")
        )
        dimensions = DimensionsVO(*sizes) if any(v is not None for v in sizes) else None
        stock = item.stock
        stock_source_id = item.id
        if parent is not None and not stock.manage_stock and parent.stock.manage_stock:
            stock = parent.stock
            stock_source_id = parent.id
        origins["stock"] = ValueOrigin(
            (
                "parent"
                if stock_source_id and stock_source_id != item.id
                else "item" if stock else "unknown"
            ),
            stock_source_id,
        )
        gallery = item.galleries.get(locale)
        gallery_owner = item.id
        if gallery is None and parent:
            gallery = parent.galleries.get(locale)
            gallery_owner = parent.id
        origins["gallery"] = ValueOrigin(
            (
                "item"
                if gallery_owner == item.id and gallery is not None
                else "parent" if gallery is not None else "unknown"
            ),
            gallery_owner if gallery else None,
            locale,
        )
        for owner in (parent, item) if parent else (item,):
            for assignment in owner.attributes:
                origins[f"attributes.{assignment.attribute_id.uuid}"] = ValueOrigin(
                    "item" if owner is item else "parent", owner.id
                )
            for entry in owner.metadata:
                origins[f"metadata.{entry.key}"] = ValueOrigin(
                    "item" if owner is item else "parent", owner.id
                )
        attrs = {a.attribute_id: a for a in parent.attributes} if parent else {}
        attrs.update({a.attribute_id: a for a in item.attributes})
        attrs = {k: v for k, v in attrs.items() if v.mode == OverrideMode.SET}
        if parent:
            for axis in parent.axes:
                origins[f"attributes.{axis.attribute_id.uuid}"] = ValueOrigin(
                    "item", item.id
                )
                option = dict(item.selection.values).get(axis.attribute_id)
                if option:
                    attrs[axis.attribute_id] = EnumAttributeAssignmentVO(
                        axis.attribute_id, (option,), axis.visible, axis.position
                    )
        metadata = (
            {
                m.key: m
                for m in sorted(parent.metadata, key=lambda m: m.position)
                if m.mode == OverrideMode.SET
            }
            if parent
            else {}
        )
        for value in sorted(item.metadata, key=lambda m: m.position):
            if value.mode == OverrideMode.CLEAR:
                metadata.pop(value.key, None)
            else:
                metadata[value.key] = value
        return EffectiveCatalogItemValues(
            content or None,
            bool(virtual),
            price,
            (
                price.at(as_of)
                if price and item.kind != CatalogItemKind.VARIABLE
                else None
            ),
            weight,
            dimensions,
            stock,
            stock_source_id,
            gallery,
            tuple(
                sorted(attrs.values(), key=lambda a: (a.position, str(a.attribute_id)))
            ),
            tuple(metadata.values()),
            item.kind != CatalogItemKind.VARIABLE
            and price is not None
            and stock.effective_status() != StockStatus.OUT_OF_STOCK
            and item.status == CatalogItemStatus.ACTIVE
            and (parent is None or parent.status == CatalogItemStatus.ACTIVE),
            item.status == CatalogItemStatus.ACTIVE
            and (parent is None or parent.status == CatalogItemStatus.ACTIVE),
            origins,
        )

    @staticmethod
    def family_summary(
        parent: CatalogItemValuesSnapshot,
        children: tuple[EffectiveCatalogItemValues, ...],
    ) -> CatalogFamilySummary:
        """Сводит активных детей без суммирования общего источника остатков."""
        active = tuple(
            c
            for c in children
            if parent.status == CatalogItemStatus.ACTIVE and c.available_for_publication
        )
        statuses = {c.stock.effective_status() for c in active}
        status = next(
            (
                v
                for v in (StockStatus.IN_STOCK, StockStatus.ON_BACKORDER)
                if v in statuses
            ),
            StockStatus.OUT_OF_STOCK,
        )
        prices = tuple(c.price for c in active if c.price is not None)
        currency = next(
            (
                c.price_specification.currency
                for c in active
                if c.price_specification is not None
            ),
            None,
        )
        return CatalogFamilySummary(
            status,
            any(c.available_for_sale for c in active),
            min(prices) if prices else None,
            max(prices) if prices else None,
            any(c.price is None for c in active),
            currency,
        )
