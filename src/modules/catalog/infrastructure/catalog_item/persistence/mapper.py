from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.infrastructure.persistence.models.catalog_item_translation import (
    CatalogItemTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_content_value import (
    CatalogItemContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_gallery import (
    CatalogItemGalleryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_image import (
    CatalogItemImageModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_attribute import (
    CatalogItemAttributeModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_attribute_option import (
    CatalogItemAttributeOptionModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_variant_selection import (
    CatalogItemVariantSelectionModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_default_selection import (
    CatalogItemDefaultSelectionModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_category import (
    CatalogItemCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_tag import (
    CatalogItemTagModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_metadata import (
    CatalogItemMetadataModel,
)

from collections.abc import Mapping
from typing import Any
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.override import (
    OverrideVO,
    OverrideMode,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockManagement,
    StockStatus,
    BackorderPolicy,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)
from src.modules.catalog.domain.catalog_item.value_object.axis import VariationAxis
from src.modules.catalog.domain.catalog_item.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute import (
    EnumAttributeAssignmentVO,
)
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.catalog_item.entity.metadata import CatalogMetadataEntry
from src.modules.catalog.domain.product_type.value_object.schema import BLOCK_IDS
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogItemMapper:
    """Чистые преобразования own-значений хранения и доменного состояния."""

    @staticmethod
    def to_values(
        row: Mapping[str, Any], parts: Mapping[str, list[dict[str, Any]]]
    ) -> CatalogItemValuesSnapshot:
        """Строит immutable снимок значений для политики без Aggregate restore."""
        identifier = row["id"]

        def rows(name: str) -> list[dict[str, Any]]:
            """Отбирает уже прочитанные batch-строки текущего узла без I/O."""
            return [
                r for r in parts.get(name, []) if r["catalog_item_id"] == identifier
            ]

        price = (
            PriceSpecificationVO(
                row["regular_price"],
                row["currency"],
                row["sale_price"],
                row["date_on_sale_from"],
                row["date_on_sale_to"],
            )
            if row["price_mode"] == "set"
            else None
        )
        dimensions = (
            DimensionsVO(row["length"], row["width"], row["height"])
            if row["dimensions_mode"] == "set"
            else None
        )
        stock = (
            StockSpecificationVO(
                StockManagement(row["manage_stock"]),
                row["stock_quantity"],
                StockStatus(row["stock_status"]) if row["stock_status"] else None,
                BackorderPolicy(row["backorders"]) if row["backorders"] else None,
            )
            if row["manage_stock"]
            else None
        )
        translations = {r["locale"]: {} for r in rows("catalog_item_translations")}
        codes = {v.uuid: k for k, v in BLOCK_IDS.items()}
        for r in rows("catalog_item_content_values"):
            translations[r["locale"]][codes[r["block_id"]]] = OverrideVO(
                OverrideMode(r["mode"]), r["value"]
            )
        galleries = {}
        images = rows("catalog_item_images")
        for gallery in rows("catalog_item_galleries"):
            members = tuple(
                CatalogItemImage.restore(
                    EntityIdVO(i["id"]),
                    EntityIdVO(i["file_id"]),
                    i["position"],
                    i["alt"],
                    i["caption"],
                )
                for i in sorted(images, key=lambda i: i["position"])
                if i["locale"] == gallery["locale"]
            )
            galleries[gallery["locale"]] = CatalogItemGallery.restore(
                members,
                (
                    EntityIdVO(gallery["primary_image_id"])
                    if gallery["primary_image_id"]
                    else None
                ),
            )
        attrs = []
        axes = []
        options = rows("catalog_item_attribute_options")
        for a in sorted(rows("catalog_item_attributes"), key=lambda a: a["position"]):
            opts = tuple(
                AttributeOptionIdVO(o["option_id"])
                for o in sorted(options, key=lambda o: o["position"])
                if o["attribute_id"] == a["attribute_id"]
            )
            if a["is_variation"]:
                axes.append(
                    VariationAxis(
                        AttributeIdVO(a["attribute_id"]),
                        opts,
                        a["position"],
                        a["visible"],
                    )
                )
            else:
                attrs.append(
                    EnumAttributeAssignmentVO(
                        AttributeIdVO(a["attribute_id"]),
                        opts,
                        a["visible"],
                        a["position"],
                        OverrideMode(a["mode"]),
                    )
                )
        selection = VariationSelectionVO(
            tuple(
                (AttributeIdVO(r["attribute_id"]), AttributeOptionIdVO(r["option_id"]))
                for r in rows("catalog_item_variant_selections")
            )
        )
        defaults = rows("catalog_item_default_selections")
        default = (
            VariationSelectionVO(
                tuple(
                    (
                        AttributeIdVO(r["attribute_id"]),
                        AttributeOptionIdVO(r["option_id"]),
                    )
                    for r in defaults
                )
            )
            if defaults
            else None
        )
        categories = rows("catalog_item_categories")
        primary = next(
            (CategoryIdVO(r["category_id"]) for r in categories if r["is_primary"]),
            None,
        )
        metadata = tuple(
            CatalogMetadataEntry.restore(
                r["key"],
                r["value_type"],
                (
                    r["text_value"]
                    if r["value_type"] == "text"
                    else (
                        r["decimal_value"]
                        if r["value_type"] == "decimal"
                        else r["boolean_value"]
                    )
                ),
                r["position"],
                OverrideMode(r["mode"]),
            )
            for r in sorted(rows("catalog_item_metadata"), key=lambda r: r["position"])
        )
        return CatalogItemValuesSnapshot(
            CatalogItemIdVO(identifier),
            CatalogItemKind(row["kind"]),
            CatalogItemIdVO(row["parent_id"]) if row["parent_id"] else None,
            EntityIdVO(row["product_type_id"]) if row["product_type_id"] else None,
            CatalogItemStatus(row["status"]),
            row["sku"],
            OverrideVO(OverrideMode(row["virtual_mode"]), row["virtual"]),
            OverrideVO(OverrideMode(row["price_mode"]), price),
            OverrideVO(OverrideMode(row["weight_mode"]), row["weight"]),
            OverrideVO(OverrideMode(row["dimensions_mode"]), dimensions),
            stock,
            translations,
            galleries,
            tuple(attrs),
            metadata,
            selection,
            tuple(axes),
            default,
            tuple(
                sorted((CategoryIdVO(r["category_id"]) for r in categories), key=str)
            ),
            CategoryIdVO.from_value(primary) if primary else None,
            tuple(
                sorted(
                    (TagIdVO(r["tag_id"]) for r in rows("catalog_item_tags")), key=str
                )
            ),
            row["revision"],
            row["created_at"],
            row["updated_at"],
            EntityIdVO(row["created_by"]),
            EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_domain(
        value: CatalogItemValuesSnapshot, children: tuple[CatalogItem, ...] = ()
    ) -> CatalogItem:
        """Восстанавливает агрегат исключительно через проверяющую фабрику."""
        return CatalogItem.restore(
            identifier=CatalogItemIdVO.from_value(value.id),
            kind=value.kind,
            parent_id=(
                CatalogItemIdVO.from_value(value.parent_id) if value.parent_id else None
            ),
            product_type_id=value.product_type_id,
            status=value.status,
            sku=SkuCodeVO(value.sku) if value.sku else None,
            virtual=value.virtual,
            price=value.price,
            weight=value.weight,
            dimensions=value.dimensions,
            stock=value.stock,
            revision=value.revision,
            created_at=value.created_at,
            updated_at=value.updated_at,
            created_by=EntityIdVO.from_value(value.created_by),
            updated_by=EntityIdVO.from_value(value.updated_by),
            translations=value.translations,
            galleries=value.galleries,
            attributes=value.attributes,
            metadata=value.metadata,
            axes=value.axes,
            selection=value.selection,
            default_selection=value.default_selection,
            category_ids=value.category_ids,
            primary_category_id=value.primary_category_id,
            tag_ids=value.tag_ids,
            children=children,
        )

    @staticmethod
    def to_insert_values(item: CatalogItem) -> dict[str, Any]:
        """Извлекает центральную строку без вычисления inherited/effective полей."""
        price = item.price.value
        dimensions = item.dimensions.value
        stock = item.stock
        return dict(
            id=item.id.uuid,
            kind=item.kind.value,
            parent_id=item.parent_id.uuid if item.parent_id else None,
            product_type_id=item.product_type_id.uuid if item.product_type_id else None,
            status=item.status.value,
            sku=item.sku.value if item.sku else None,
            revision=item.revision,
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by.uuid,
            updated_by=item.updated_by.uuid,
            virtual_mode=item.virtual.mode.value,
            virtual=item.virtual.value,
            price_mode=item.price.mode.value,
            regular_price=price.regular_price if price else None,
            sale_price=price.sale_price if price else None,
            currency=price.currency if price else None,
            date_on_sale_from=price.date_on_sale_from if price else None,
            date_on_sale_to=price.date_on_sale_to if price else None,
            weight_mode=item.weight.mode.value,
            weight=item.weight.value,
            dimensions_mode=item.dimensions.mode.value,
            length=dimensions.length if dimensions else None,
            width=dimensions.width if dimensions else None,
            height=dimensions.height if dimensions else None,
            manage_stock=stock.manage_stock.value if stock else None,
            stock_quantity=stock.stock_quantity if stock else None,
            stock_status=(
                stock.stock_status.value if stock and stock.stock_status else None
            ),
            backorders=stock.backorders.value if stock and stock.backorders else None,
        )

    @staticmethod
    def to_parts(item: CatalogItem) -> dict[str, list[dict[str, Any]]]:
        """Разбирает принадлежащие компоненты на нормализованные собственные строки."""
        identifier = item.id.uuid
        parts = {
            model.__table__.name: []
            for model in (
                CatalogItemTranslationModel,
                CatalogItemContentValueModel,
                CatalogItemGalleryModel,
                CatalogItemImageModel,
                CatalogItemAttributeModel,
                CatalogItemAttributeOptionModel,
                CatalogItemVariantSelectionModel,
                CatalogItemDefaultSelectionModel,
                CatalogItemCategoryModel,
                CatalogItemTagModel,
                CatalogItemMetadataModel,
            )
        }
        for locale, values in item.translations.items():
            parts["catalog_item_translations"].append(
                dict(catalog_item_id=identifier, locale=locale)
            )
            for code, value in sorted(values.items()):
                parts["catalog_item_content_values"].append(
                    dict(
                        catalog_item_id=identifier,
                        locale=locale,
                        block_id=BLOCK_IDS[code].uuid,
                        mode=value.mode.value,
                        value=value.value,
                    )
                )
        for locale, gallery in item.galleries.items():
            parts["catalog_item_galleries"].append(
                dict(
                    catalog_item_id=identifier,
                    locale=locale,
                    primary_image_id=(
                        gallery.primary_image_id.uuid
                        if gallery.primary_image_id
                        else None
                    ),
                )
            )
            for image in sorted(gallery.images, key=lambda i: i.position):
                parts["catalog_item_images"].append(
                    dict(
                        id=image.id.uuid,
                        catalog_item_id=identifier,
                        locale=locale,
                        file_id=image.file_id.uuid,
                        position=image.position,
                        alt=image.alt,
                        caption=image.caption,
                    )
                )
        assignments = [
            (a.attribute_id, a.option_ids, a.position, a.visible, False, a.mode.value)
            for a in item.attributes
        ]
        assignments.extend(
            (a.attribute_id, a.option_ids, a.position, a.visible, True, "set")
            for a in item.axes
        )
        for attribute, options, position, visible, variation, mode in assignments:
            parts["catalog_item_attributes"].append(
                dict(
                    catalog_item_id=identifier,
                    attribute_id=attribute.uuid,
                    position=position,
                    visible=visible,
                    is_variation=variation,
                    mode=mode,
                )
            )
            parts["catalog_item_attribute_options"].extend(
                dict(
                    catalog_item_id=identifier,
                    attribute_id=attribute.uuid,
                    option_id=o.uuid,
                    position=i,
                    is_variation=variation,
                )
                for i, o in enumerate(options)
            )
        parts["catalog_item_variant_selections"] = [
            dict(
                catalog_item_id=identifier,
                parent_id=item.parent_id.uuid,
                attribute_id=a.uuid,
                option_id=o.uuid,
                is_variation=True,
            )
            for a, o in item.selection.values
        ]
        parts["catalog_item_default_selections"] = (
            [
                dict(
                    catalog_item_id=identifier,
                    attribute_id=a.uuid,
                    option_id=o.uuid,
                    is_variation=True,
                )
                for a, o in item.default_selection.values
            ]
            if item.default_selection
            else []
        )
        parts["catalog_item_categories"] = [
            dict(
                catalog_item_id=identifier,
                category_id=c.uuid,
                is_primary=c == item.primary_category_id,
            )
            for c in sorted(item.category_ids, key=str)
        ]
        parts["catalog_item_tags"] = [
            dict(catalog_item_id=identifier, tag_id=t.uuid)
            for t in sorted(item.tag_ids, key=str)
        ]
        for entry in item.metadata:
            parts["catalog_item_metadata"].append(
                dict(
                    catalog_item_id=identifier,
                    key=entry.key,
                    mode=entry.mode.value,
                    value_type=entry.value_type,
                    text_value=entry.value if entry.value_type == "text" else None,
                    decimal_value=(
                        entry.value if entry.value_type == "decimal" else None
                    ),
                    boolean_value=(
                        entry.value if entry.value_type == "boolean" else None
                    ),
                    position=entry.position,
                )
            )
        return parts
