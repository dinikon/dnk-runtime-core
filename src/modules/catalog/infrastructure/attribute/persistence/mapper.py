from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.catalog.domain.attribute.aggregate import AttributeDefinition
from src.modules.catalog.domain.attribute.entity.option import AttributeOption
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class AttributeMapper:
    """Чистое преобразование представления хранения полного определения."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any],
        translations: dict[str, str],
        options: Sequence[Mapping[str, Any]],
    ) -> AttributeDefinition:
        """Восстанавливает агрегат через явные фабрики без исправления инвариантов."""
        return AttributeDefinition.restore(
            identifier=AttributeIdVO(row["id"]),
            code=row["code"],
            translations=translations,
            options=tuple(
                AttributeOption.restore(
                    AttributeOptionIdVO(o["id"]), o["code"], o["translations"]
                )
                for o in options
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_insert_values(entity: AttributeDefinition) -> dict[str, Any]:
        """Извлекает первоначальные поля без выполнения SQL."""
        return {
            "id": entity.id.uuid,
            "revision": 1,
            "code": entity.code.value,
            "created_at": entity.created_at,
            "created_by": entity.created_by.uuid,
            **AttributeMapper.to_update_values(entity),
        }

    @staticmethod
    def to_update_values(entity: AttributeDefinition) -> dict[str, Any]:
        """Извлекает изменяемое доменное состояние для хранения."""
        return {
            "updated_at": entity.updated_at,
            "updated_by": entity.updated_by.uuid,
        }
