from typing import Any
from collections.abc import Mapping
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.aggregate import ProductKind
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProductMapper:
    """Чистое преобразование хранения; инварианты проверяет restore."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any],
        variant: Mapping[str, Any],
        translations: dict[str, dict[str, str]],
    ) -> Product:
        """Восстанавливает сохранённый агрегат без событий создания."""
        return Product.restore(
            identifier=ProductIdVO(row["id"]),
            kind=ProductKind(row["kind"]),
            product_type_id=ProductTypeIdVO(row["product_type_id"]),
            variant=Variant.restore(
                VariantIdVO(variant["id"]),
                variant["virtual"],
                variant["downloadable"],
                variant["translations"],
            ),
            translations=translations,
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_insert_values(entity: Product) -> dict[str, Any]:
        """Извлекает значения для INSERT без I/O."""
        return {
            "id": entity.id.uuid,
            "created_at": entity.created_at,
            "created_by": entity.created_by.uuid,
            **ProductMapper.to_update_values(entity),
        }

    @staticmethod
    def to_update_values(entity: Product) -> dict[str, Any]:
        """Извлекает доменное состояние для UPDATE без бизнес-решений."""
        return {
            "kind": entity.kind.value,
            "product_type_id": entity.product_type_id.uuid,
            "revision": entity.revision,
            "updated_at": entity.updated_at,
            "updated_by": entity.updated_by.uuid,
        }

    @staticmethod
    def variant_values(entity: Product) -> dict[str, Any]:
        """Подготавливает хранение внутренней позиции без собственного repository."""
        return {
            "id": entity.variant.id.uuid,
            "product_id": entity.id.uuid,
            "virtual": entity.variant.virtual,
            "downloadable": entity.variant.downloadable,
        }
