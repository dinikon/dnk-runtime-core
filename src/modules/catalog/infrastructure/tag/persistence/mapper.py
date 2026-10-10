from collections.abc import Mapping
from typing import Any
from src.modules.catalog.domain.tag.aggregate import Tag
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class TagMapper:
    """Чистое преобразование хранения tag через доменную фабрику."""

    @staticmethod
    def to_domain(row: Mapping[str, Any], translations: dict[str, str]) -> Tag:
        """Передаёт полное состояние фабрике без исправления инвариантов."""
        return Tag.restore(
            identifier=TagIdVO(row["id"]),
            translations=translations,
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_insert_values(entity: Tag) -> dict[str, Any]:
        """Извлекает поля нового корня без I/O."""
        return {
            "id": entity.id.uuid,
            "created_at": entity.created_at,
            "created_by": entity.created_by.uuid,
            **TagMapper.to_update_values(entity),
        }

    @staticmethod
    def to_update_values(entity: Tag) -> dict[str, Any]:
        """Извлекает проверенное состояние для UPDATE."""
        return {
            "revision": entity.revision,
            "updated_at": entity.updated_at,
            "updated_by": entity.updated_by.uuid,
        }
