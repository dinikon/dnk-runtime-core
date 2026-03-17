from __future__ import annotations

from src.modules.runtime_schema.application.dto import (
    DataSourceDTO,
    FieldMetadataDTO,
    ObjectMetadataDTO,
)
from src.modules.runtime_schema.domain.entities import (
    DataSource,
    FieldMetadata,
    ObjectMetadata,
)


def data_source_to_dto(data_source: DataSource) -> DataSourceDTO:
    return DataSourceDTO(
        id=data_source.id,
        created_at=data_source.created_at,
        updated_at=data_source.updated_at,
        tenant_id=data_source.tenant_id,
        source_type=data_source.type.value,
        schema=data_source.schema,
        url=data_source.url,
    )


def object_metadata_to_dto(object_metadata: ObjectMetadata) -> ObjectMetadataDTO:
    return ObjectMetadataDTO(
        id=object_metadata.id,
        created_at=object_metadata.created_at,
        updated_at=object_metadata.updated_at,
        tenant_id=object_metadata.tenant_id,
        data_source_id=object_metadata.data_source_id,
        name_singular=object_metadata.name_singular,
        name_plural=object_metadata.name_plural,
        label_singular=object_metadata.label_singular,
        label_plural=object_metadata.label_plural,
        description=object_metadata.description,
        icon=object_metadata.icon,
        is_system=object_metadata.is_system,
        duplicate_criteria=object_metadata.duplicate_criteria,
        shortcut=object_metadata.shortcut,
        ownership_kind=object_metadata.ownership_kind.value,
        allows_custom_fields=object_metadata.allows_custom_fields,
    )


def field_metadata_to_dto(field_metadata: FieldMetadata) -> FieldMetadataDTO:
    return FieldMetadataDTO(
        id=field_metadata.id,
        created_at=field_metadata.created_at,
        updated_at=field_metadata.updated_at,
        object_metadata_id=field_metadata.object_metadata_id,
        field_type=field_metadata.type.value,
        name=field_metadata.name,
        label=field_metadata.label,
        default_value=field_metadata.default_value,
        description=field_metadata.description,
        icon=field_metadata.icon,
        options=field_metadata.options,
        settings=dict(field_metadata.settings),
        is_active=field_metadata.is_active,
        is_nullable=field_metadata.is_nullable,
        is_unique=field_metadata.is_unique,
        tenant_id=field_metadata.tenant_id,
    )


__all__ = [
    "data_source_to_dto",
    "field_metadata_to_dto",
    "object_metadata_to_dto",
]
