from collections.abc import Mapping
from typing import Any
from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CategoryMapper:
    """Чистое преобразование хранения category через доменную фабрику."""

    @staticmethod
    def to_domain(row: Mapping[str, Any], translations: dict[str, str]) -> Category:
        """Передаёт полное состояние фабрике без исправления инвариантов."""
        return Category.restore(
            identifier=CategoryIdVO(row["id"]),
            parent_id=(
                None if row["parent_id"] is None else CategoryIdVO(row["parent_id"])
            ),
            translations=translations,
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_insert_values(entity: Category) -> dict[str, Any]:
        """Извлекает поля нового корня без I/O."""
        return {
            "id": entity.id.uuid,
            "created_at": entity.created_at,
            "created_by": entity.created_by.uuid,
            **CategoryMapper.to_update_values(entity),
        }

    @staticmethod
    def to_update_values(entity: Category) -> dict[str, Any]:
        """Извлекает проверенное состояние для UPDATE."""
        return {
            "parent_id": None if entity.parent_id is None else entity.parent_id.uuid,
            "revision": entity.revision,
            "updated_at": entity.updated_at,
            "updated_by": entity.updated_by.uuid,
        }
