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
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockStatus,
    BackorderPolicy,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
    WeightVO,
    WeightUnit,
    LengthVO,
    LengthUnit,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
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
    """Чистые преобразования значений хранения и доменного состояния."""

    @staticmethod
    def to_values(
        row: Mapping[str, Any], parts: Mapping[str, list[dict[str, Any]]]
    ) -> CatalogItemValuesSnapshot:
        """Строит immutable снимок значений для политики без Aggregate restore."""
        identifier = row["id"]

        def rows(name: str) -> list[dict[str, Any]]:
            """Отбирает уже прочитанные batch-строки текущего товара без I/O."""
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
            if row["regular_price"] is not None
            else None
        )
        sizes = tuple(
            (
                LengthVO(row[name], LengthUnit(row[f"{name}_unit"]))
                if row[name] is not None
                else None
            )
            for name in ("length", "width", "height")
        )
        dimensions = DimensionsVO(*sizes) if any(v is not None for v in sizes) else None
        stock = StockSpecificationVO(
            row["manage_stock"],
            row["stock_quantity"],
            StockStatus(row["stock_status"]) if row["stock_status"] else None,
            BackorderPolicy(row["backorders"]),
        )
        translations = {r["locale"]: {} for r in rows("catalog_item_translations")}
        codes = {v.uuid: k for k, v in BLOCK_IDS.items()}
        for r in rows("catalog_item_content_values"):
            if r["mode"] == "set":
                translations[r["locale"]][codes[r["block_id"]]] = r["value"]
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
        options = rows("catalog_item_attribute_options")
        for assignment in sorted(
            rows("catalog_item_attributes"), key=lambda a: a["position"]
        ):
            if assignment["mode"] != "set":
                continue
            attrs.append(
                EnumAttributeAssignmentVO(
                    AttributeIdVO(assignment["attribute_id"]),
                    tuple(
                        AttributeOptionIdVO(o["option_id"])
                        for o in sorted(options, key=lambda o: o["position"])
                        if o["attribute_id"] == assignment["attribute_id"]
                    ),
                    assignment["visible"],
                    assignment["position"],
                )
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
            )
            for r in sorted(rows("catalog_item_metadata"), key=lambda r: r["position"])
            if r["mode"] == "set"
        )
        return CatalogItemValuesSnapshot(
            id=CatalogItemIdVO(identifier),
            product_type_id=EntityIdVO(row["product_type_id"]),
            status=CatalogItemStatus(row["status"]),
            sku=row["sku"],
            virtual=row["virtual"],
            price=price,
            weight=(
                WeightVO(row["weight"], WeightUnit(row["weight_unit"]))
                if row["weight"] is not None
                else None
            ),
            dimensions=dimensions,
            stock=stock,
            translations=translations,
            galleries=galleries,
            attributes=tuple(attrs),
            metadata=metadata,
            category_ids=tuple(
                sorted((CategoryIdVO(r["category_id"]) for r in categories), key=str)
            ),
            primary_category_id=primary,
            tag_ids=tuple(
                sorted(
                    (TagIdVO(r["tag_id"]) for r in rows("catalog_item_tags")), key=str
                )
            ),
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_domain(value: CatalogItemValuesSnapshot) -> CatalogItem:
        """Восстанавливает агрегат исключительно через проверяющую фабрику."""
        return CatalogItem.restore(
            identifier=CatalogItemIdVO.from_value(value.id),
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
            category_ids=value.category_ids,
            primary_category_id=value.primary_category_id,
            tag_ids=value.tag_ids,
        )

    @staticmethod
    def to_insert_values(item: CatalogItem) -> dict[str, Any]:
        """Извлекает центральную строку без вычисления вычисляемых полей."""
        price = item.price
        dimensions = item.dimensions
        stock = item.stock
        return dict(
            id=item.id.uuid,
            kind="simple",
            parent_id=None,
            product_type_id=item.product_type_id.uuid if item.product_type_id else None,
            status=item.status.value,
            sku=item.sku.value if item.sku else None,
            revision=item.revision,
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by.uuid,
            updated_by=item.updated_by.uuid,
            virtual=item.virtual,
            regular_price=price.regular_price if price else None,
            sale_price=price.sale_price if price else None,
            currency=price.currency if price else None,
            date_on_sale_from=price.date_on_sale_from if price else None,
            date_on_sale_to=price.date_on_sale_to if price else None,
            weight=item.weight.value if item.weight else None,
            weight_unit=item.weight.unit.value if item.weight else None,
            length=(
                dimensions.length.value if dimensions and dimensions.length else None
            ),
            length_unit=(
                dimensions.length.unit.value
                if dimensions and dimensions.length
                else None
            ),
            width=dimensions.width.value if dimensions and dimensions.width else None,
            width_unit=(
                dimensions.width.unit.value if dimensions and dimensions.width else None
            ),
            height=(
                dimensions.height.value if dimensions and dimensions.height else None
            ),
            height_unit=(
                dimensions.height.unit.value
                if dimensions and dimensions.height
                else None
            ),
            manage_stock=stock.manage_stock,
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
                        mode="set",
                        value=value,
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
        for assignment in item.attributes:
            parts["catalog_item_attributes"].append(
                dict(
                    catalog_item_id=identifier,
                    attribute_id=assignment.attribute_id.uuid,
                    position=assignment.position,
                    visible=assignment.visible,
                    is_variation=False,
                    mode="set",
                )
            )
            parts["catalog_item_attribute_options"].extend(
                dict(
                    catalog_item_id=identifier,
                    attribute_id=assignment.attribute_id.uuid,
                    option_id=option.uuid,
                    position=position,
                    is_variation=False,
                )
                for position, option in enumerate(assignment.option_ids)
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
                    mode="set",
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
