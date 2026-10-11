from datetime import datetime
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
    EffectiveCatalogItemValues,
    ValueOrigin,
)
from src.modules.catalog.domain.catalog_item.value_object.override import (
    OverrideMode,
    OverrideVO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import StockManagement
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

        def scalar(
            name: str, own: OverrideVO, inherited: OverrideVO | None
        ) -> object | None:
            """Разрешает явно типизированную группу без truthy-проверок."""
            value = own
            source_id = item.id
            source = "item"
            if own.mode == OverrideMode.INHERIT:
                value = inherited
                source_id = parent.id if parent else None
                source = "parent"
            if value is None or value.mode != OverrideMode.SET:
                origins[name] = ValueOrigin(
                    "unknown" if own.mode != OverrideMode.CLEAR else "item", source_id
                )
                return None
            origins[name] = ValueOrigin(source, source_id)
            return value.value

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
        virtual = scalar("virtual", item.virtual, parent.virtual if parent else None)
        price = scalar("price", item.price, parent.price if parent else None)
        weight = scalar("weight", item.weight, parent.weight if parent else None)
        dimensions = scalar(
            "dimensions", item.dimensions, parent.dimensions if parent else None
        )
        stock = item.stock
        stock_source_id = item.id if stock else None
        if stock and stock.manage_stock == StockManagement.PARENT:
            if (
                parent is None
                or parent.stock is None
                or parent.stock.manage_stock != StockManagement.OWN
            ):
                raise InvalidCatalogValueError(
                    "Parent требует собственный источник наличия VARIABLE."
                )
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
            item.status == CatalogItemStatus.ACTIVE
            and (parent is None or parent.status == CatalogItemStatus.ACTIVE),
            origins,
        )
