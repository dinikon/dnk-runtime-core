from __future__ import annotations

from uuid import UUID

from src.modules.runtime_schema.domain.entities import (
    DataSource,
    FieldMetadata,
    ObjectMetadata,
)
from src.modules.runtime_schema.domain.value_objects import (
    DataSourceType,
    FieldType,
    ObjectOwnershipKind,
)
from src.modules.runtime_schema.infrastructure.persistence import (
    RuntimeDataSourceMetadataModel,
    RuntimeFieldMetadataModel,
    RuntimeObjectMetadataModel,
)


def data_source_to_model(data_source: DataSource) -> RuntimeDataSourceMetadataModel:
    return RuntimeDataSourceMetadataModel(
        id=data_source.id,
        created_at=data_source.created_at,
        updated_at=data_source.updated_at,
        tenant_id=data_source.tenant_id,
        source_type=data_source.type.value,
        schema=data_source.schema,
        url=data_source.url,
    )


def data_source_model_to_entity(model: RuntimeDataSourceMetadataModel) -> DataSource:
    return DataSource(
        id=_to_uuid(model.id),
        created_at=model.created_at,
        updated_at=model.updated_at,
        tenant_id=_to_uuid(model.tenant_id),
        type=DataSourceType(model.source_type),
        schema=model.schema,
        url=model.url,
    )


def object_metadata_to_model(
    object_metadata: ObjectMetadata,
) -> RuntimeObjectMetadataModel:
    return RuntimeObjectMetadataModel(
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


def object_metadata_model_to_entity(
    model: RuntimeObjectMetadataModel,
) -> ObjectMetadata:
    return ObjectMetadata(
        id=_to_uuid(model.id),
        created_at=model.created_at,
        updated_at=model.updated_at,
        tenant_id=_to_uuid(model.tenant_id),
        data_source_id=_to_uuid(model.data_source_id),
        name_singular=model.name_singular,
        name_plural=model.name_plural,
        label_singular=model.label_singular,
        label_plural=model.label_plural,
        description=model.description,
        icon=model.icon,
        is_system=model.is_system,
        duplicate_criteria=model.duplicate_criteria,
        shortcut=model.shortcut,
        ownership_kind=ObjectOwnershipKind(model.ownership_kind),
        allows_custom_fields=model.allows_custom_fields,
    )


def field_metadata_to_model(field_metadata: FieldMetadata) -> RuntimeFieldMetadataModel:
    return RuntimeFieldMetadataModel(
        id=field_metadata.id,
        created_at=field_metadata.created_at,
        updated_at=field_metadata.updated_at,
        object_metadata_id=field_metadata.object_metadata_id,
        tenant_id=field_metadata.tenant_id,
        field_type=field_metadata.type.value,
        name=field_metadata.name,
        label=field_metadata.label,
        default_value=field_metadata.default_value,
        description=field_metadata.description,
        icon=field_metadata.icon,
        options=list(field_metadata.options),
        settings=dict(field_metadata.settings),
        is_active=field_metadata.is_active,
        is_nullable=field_metadata.is_nullable,
        is_unique=field_metadata.is_unique,
    )


def field_metadata_model_to_entity(model: RuntimeFieldMetadataModel) -> FieldMetadata:
    return FieldMetadata(
        id=_to_uuid(model.id),
        created_at=model.created_at,
        updated_at=model.updated_at,
        object_metadata_id=_to_uuid(model.object_metadata_id),
        tenant_id=_to_uuid(model.tenant_id),
        type=FieldType(model.field_type),
        name=model.name,
        label=model.label,
        default_value=model.default_value,
        description=model.description,
        icon=model.icon,
        options=tuple(model.options or ()),
        settings=dict(model.settings or {}),
        is_active=model.is_active,
        is_nullable=model.is_nullable,
        is_unique=model.is_unique,
    )


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


__all__ = [
    "data_source_model_to_entity",
    "data_source_to_model",
    "field_metadata_model_to_entity",
    "field_metadata_to_model",
    "object_metadata_model_to_entity",
    "object_metadata_to_model",
]
