from typing import Any
from collections.abc import Mapping, Sequence
from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.value_object.block_link import (
    ProductTypeContentBlock,
    ContentScope,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProductTypeMapper:
    """Чистое преобразование хранения; инварианты проверяет restore."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any],
        links: Sequence[Mapping[str, Any]],
        translations: dict[str, str],
    ) -> ProductType:
        """Восстанавливает сохранённый агрегат без событий создания."""
        return ProductType.restore(
            identifier=ProductTypeIdVO(row["id"]),
            code=row["code"],
            is_system=row["is_system"],
            schema_version=row["schema_version"],
            blocks=tuple(
                ProductTypeContentBlock(
                    ContentBlockIdVO(b["block_id"]),
                    ContentScope(b["scope"]),
                    b["required"],
                    b["position"],
                )
                for b in links
            ),
            translations=translations,
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_insert_values(entity: ProductType) -> dict[str, Any]:
        """Извлекает значения для INSERT без I/O."""
        return {
            "id": entity.id.uuid,
            "created_at": entity.created_at,
            "created_by": entity.created_by.uuid,
            **ProductTypeMapper.to_update_values(entity),
        }

    @staticmethod
    def to_update_values(entity: ProductType) -> dict[str, Any]:
        """Извлекает доменное состояние для UPDATE без бизнес-решений."""
        return {
            "code": entity.code.value,
            "is_system": entity.is_system,
            "schema_version": entity.schema_version,
            "revision": entity.revision,
            "updated_at": entity.updated_at,
            "updated_by": entity.updated_by.uuid,
        }

    @staticmethod
    def link_values(entity: ProductType) -> list[dict[str, Any]]:
        """Подготавливает хранение внутренних связей схемы."""
        return [
            {
                "product_type_id": entity.id.uuid,
                "block_id": b.block_id.uuid,
                "scope": b.scope.value,
                "required": b.required,
                "position": b.position,
            }
            for b in entity.blocks
        ]
