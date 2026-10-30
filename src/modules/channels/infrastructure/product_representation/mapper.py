from collections.abc import Mapping
from typing import Any

from src.modules.channels.application.product_representation.contracts import (
    RepresentationState,
)
from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.infrastructure.product_representation.document import (
    decode_overrides,
    encode_overrides,
    OVERRIDES_SCHEMA,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProductRepresentationMapper:
    """Разделяет восстановление агрегата, read-проекцию и значения записи без I/O."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ProductRepresentation:
        """Передаёт проверки состояния явной доменной фабрике."""
        return ProductRepresentation.restore(
            identifier=EntityIdVO(row["id"]),
            binding_group_id=EntityIdVO(row["binding_group_id"]),
            revision=row["revision"],
            export_enabled=row["export_enabled"],
            overrides=decode_overrides(
                schema=row["overrides_schema"], document=row["overrides_data"]
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_state(row: Mapping[str, Any]) -> RepresentationState:
        """Создаёт read DTO без восстановления агрегата."""
        return RepresentationState(
            id=row["id"],
            revision=row["revision"],
            export_enabled=row["export_enabled"],
            overrides=decode_overrides(
                schema=row["overrides_schema"], document=row["overrides_data"]
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )

    @staticmethod
    def to_values(value: ProductRepresentation) -> dict[str, Any]:
        """Перечисляет все поля хранения, не сохраняя вычисленный контент."""
        return {
            "id": value.id.uuid,
            "binding_group_id": value.binding_group_id.uuid,
            "revision": value.revision,
            "export_enabled": value.export_enabled,
            "overrides_schema": OVERRIDES_SCHEMA,
            "overrides_data": encode_overrides(value.overrides),
            "created_at": value.created_at,
            "updated_at": value.updated_at,
            "created_by": value.created_by.uuid,
            "updated_by": value.updated_by.uuid,
        }
