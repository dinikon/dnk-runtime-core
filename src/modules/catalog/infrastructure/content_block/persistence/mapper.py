from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)
from typing import Any
from collections.abc import Mapping
from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentBlockMapper:
    """Чистое преобразование хранения; инварианты проверяет restore."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any], translations: dict[str, str]
    ) -> ContentBlockDefinition:
        """Восстанавливает сохранённый агрегат без событий создания."""
        return ContentBlockDefinition.restore(
            identifier=ContentBlockIdVO(row["id"]),
            code=row["code"],
            is_system=row["is_system"],
            value_type=ContentValueType(row["value_type"]),
            translations=translations,
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_insert_values(entity: ContentBlockDefinition) -> dict[str, Any]:
        """Извлекает значения для INSERT без I/O."""
        return {
            "id": entity.id.uuid,
            "created_at": entity.created_at,
            "created_by": entity.created_by.uuid,
            **ContentBlockMapper.to_update_values(entity),
        }

    @staticmethod
    def to_update_values(entity: ContentBlockDefinition) -> dict[str, Any]:
        """Извлекает доменное состояние для UPDATE без бизнес-решений."""
        return {
            "code": entity.code.value,
            "is_system": entity.is_system,
            "value_type": entity.value_type.value,
            "revision": entity.revision,
            "updated_at": entity.updated_at,
            "updated_by": entity.updated_by.uuid,
        }
