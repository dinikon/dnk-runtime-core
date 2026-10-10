from src.modules.catalog.domain.product.value_object.attribute_value import (
    ProductAttributeValueVO,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from typing import Any
from collections.abc import Mapping
from src.modules.catalog.domain.product.aggregate import Product, ProductKind
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.product.value_object.axis import VariationAxis
from src.modules.catalog.domain.product.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.catalog.domain.product.entity.structure import (
    SimpleProductStructure,
    VariableProductStructure,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProductMapper:
    """Чистое преобразование хранения; инварианты проверяет Product.restore."""

    @staticmethod
    def _selection(values: Mapping[str, str]) -> VariationSelectionVO:
        """Преобразует хранимые идентичности в неизменяемое значение."""
        return VariationSelectionVO(
            tuple(
                (AttributeIdVO.from_value(a), AttributeOptionIdVO.from_value(o))
                for a, o in values.items()
            )
        )

    @staticmethod
    def to_domain(
        row: Mapping[str, Any],
        parts: Mapping[str, Any],
        translations: dict[str, dict[str, str]],
    ) -> Product:
        """Восстанавливает все позиции без исправления структуры или генерации ID."""
        variants = tuple(
            Variant.restore(
                VariantIdVO(v["id"]),
                v["virtual"],
                v["downloadable"],
                v["translations"],
                ProductMapper._selection(v["selection"]),
            )
            for v in parts["variants"]
        )
        kind = ProductKind(row["kind"])
        axes = tuple(
            VariationAxis(
                AttributeIdVO(a["attribute_id"]),
                tuple(AttributeOptionIdVO(o) for o in a["option_ids"]),
                a["position"],
            )
            for a in parts["axes"]
        )
        default = (
            None
            if parts["default_selection"] is None
            else ProductMapper._selection(parts["default_selection"])
        )
        structure = (
            SimpleProductStructure.restore(variants, axes, default)
            if kind == ProductKind.SIMPLE
            else VariableProductStructure.restore(axes, default, variants)
        )
        return Product.restore(
            identifier=ProductIdVO(row["id"]),
            kind=kind,
            product_type_id=ProductTypeIdVO(row["product_type_id"]),
            structure=structure,
            translations=translations,
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
            attribute_values=tuple(
                ProductAttributeValueVO(
                    AttributeIdVO(v["attribute_id"]),
                    AttributeOptionIdVO(v["option_id"]),
                    v["visible"],
                    v["position"],
                )
                for v in parts["attribute_values"]
            ),
            category_ids=tuple(
                CategoryIdVO(c["category_id"]) for c in parts["categories"]
            ),
            primary_category_ids=tuple(
                CategoryIdVO(c["category_id"])
                for c in parts["categories"]
                if c["is_primary"]
            ),
            tag_ids=tuple(TagIdVO(t) for t in parts["tag_ids"]),
        )

    @staticmethod
    def to_insert_values(entity: Product) -> dict[str, Any]:
        """Извлекает поля INSERT без I/O."""
        return {
            "id": entity.id.uuid,
            "created_at": entity.created_at,
            "created_by": entity.created_by.uuid,
            **ProductMapper.to_update_values(entity),
        }

    @staticmethod
    def to_update_values(entity: Product) -> dict[str, Any]:
        """Извлекает доменное состояние UPDATE без бизнес-решений."""
        return {
            "kind": entity.kind.value,
            "product_type_id": entity.product_type_id.uuid,
            "revision": entity.revision,
            "updated_at": entity.updated_at,
            "updated_by": entity.updated_by.uuid,
        }

    @staticmethod
    def variant_values(product_id: ProductIdVO, variant: Variant) -> dict[str, Any]:
        """Извлекает строку принадлежащей позиции без отдельного repository."""
        return {
            "id": variant.id.uuid,
            "product_id": product_id.uuid,
            "virtual": variant.virtual,
            "downloadable": variant.downloadable,
        }
