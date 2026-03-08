from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.domain.entities import FieldMetadata, ObjectMetadata
from src.modules.runtime_schema.domain.value_objects.field_type import (
    RuntimeSchemaFieldType,
)
from src.modules.runtime_schema.infrastructure.persistence.field_metadata import (
    FieldMetadataModel,
)
from src.modules.runtime_schema.infrastructure.persistence.object_metadata import (
    ObjectMetadataModel,
)


class SqlAlchemyObjectMetadataRepository(ObjectMetadataRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, object_metadata: ObjectMetadata) -> None:
        self._session.add(
            ObjectMetadataModel(
                id=object_metadata.id,
                tenant_id=object_metadata.tenant_id,
                data_source_id=object_metadata.data_source_id,
                name_singular=object_metadata.name_singular,
                name_plural=object_metadata.name_plural,
                label_singular=object_metadata.label_singular,
                label_plural=object_metadata.label_plural,
                description=object_metadata.description,
                icon=object_metadata.icon,
                is_custom=object_metadata.is_custom,
                is_remote=object_metadata.is_remote,
                is_active=object_metadata.is_active,
                is_system=object_metadata.is_system,
                is_ui_read_only=object_metadata.is_ui_read_only,
                is_audit_logged=object_metadata.is_audit_logged,
                is_searchable=object_metadata.is_searchable,
                duplicate_criteria=object_metadata.duplicate_criteria,
                shortcut=object_metadata.shortcut,
                label_identifier_field_metadata_id=object_metadata.label_identifier_field_metadata_id,
                created_at=object_metadata.created_at,
                updated_at=object_metadata.updated_at,
            )
        )
        await self._session.flush()

    async def save(self, object_metadata: ObjectMetadata) -> None:
        model = await self._session.get(ObjectMetadataModel, object_metadata.id)
        if model is None:
            return
        model.label_identifier_field_metadata_id = (
            object_metadata.label_identifier_field_metadata_id
        )
        model.updated_at = object_metadata.updated_at
        await self._session.flush()

    async def get_by_tenant_and_name_singular(
        self,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None:
        model = await self._session.scalar(
            select(ObjectMetadataModel)
            .where(ObjectMetadataModel.tenant_id == str(tenant_id))
            .where(ObjectMetadataModel.name_singular == name_singular)
            .limit(1)
        )
        if model is None:
            return None
        return self._map_object(model)

    @staticmethod
    def _map_object(model: ObjectMetadataModel) -> ObjectMetadata:
        return ObjectMetadata(
            id=_to_uuid(model.id),
            tenant_id=_to_uuid(model.tenant_id),
            data_source_id=_to_uuid(model.data_source_id),
            name_singular=model.name_singular,
            name_plural=model.name_plural,
            label_singular=model.label_singular,
            label_plural=model.label_plural,
            description=model.description,
            icon=model.icon,
            is_custom=model.is_custom,
            is_remote=model.is_remote,
            is_active=model.is_active,
            is_system=model.is_system,
            is_ui_read_only=model.is_ui_read_only,
            is_audit_logged=model.is_audit_logged,
            is_searchable=model.is_searchable,
            duplicate_criteria=model.duplicate_criteria,
            shortcut=model.shortcut,
            label_identifier_field_metadata_id=_to_uuid(
                model.label_identifier_field_metadata_id
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyFieldMetadataRepository(FieldMetadataRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, field_metadata: FieldMetadata) -> None:
        self._session.add(
            FieldMetadataModel(
                id=field_metadata.id,
                tenant_id=field_metadata.tenant_id,
                object_metadata_id=field_metadata.object_metadata_id,
                type=field_metadata.field_type.value,
                name_field=field_metadata.name_field,
                label=field_metadata.label,
                default_value=field_metadata.default_value,
                description=field_metadata.description,
                icon=field_metadata.icon,
                options=field_metadata.options,
                settings=field_metadata.settings,
                is_custom=field_metadata.is_custom,
                is_active=field_metadata.is_active,
                is_system=field_metadata.is_system,
                is_ui_read_only=field_metadata.is_ui_read_only,
                is_nullable=field_metadata.is_nullable,
                is_unique=field_metadata.is_unique,
                relation_target_field_metadata_id=field_metadata.relation_target_field_metadata_id,
                relation_target_object_metadata_id=field_metadata.relation_target_object_metadata_id,
                created_at=field_metadata.created_at,
                updated_at=field_metadata.updated_at,
            )
        )
        await self._session.flush()

    async def save(self, field_metadata: FieldMetadata) -> None:
        model = await self._session.get(FieldMetadataModel, field_metadata.id)
        if model is None:
            return
        model.relation_target_field_metadata_id = (
            field_metadata.relation_target_field_metadata_id
        )
        model.relation_target_object_metadata_id = (
            field_metadata.relation_target_object_metadata_id
        )
        model.updated_at = field_metadata.updated_at
        await self._session.flush()

    async def get_by_object_and_name_field(
        self,
        object_metadata_id: UUID,
        name_field: str,
    ) -> FieldMetadata | None:
        model = await self._session.scalar(
            select(FieldMetadataModel)
            .where(FieldMetadataModel.object_metadata_id == str(object_metadata_id))
            .where(FieldMetadataModel.name_field == name_field)
            .limit(1)
        )
        if model is None:
            return None
        return self._map_field(model)

    @staticmethod
    def _map_field(model: FieldMetadataModel) -> FieldMetadata:
        return FieldMetadata(
            id=_to_uuid(model.id),
            tenant_id=_to_uuid(model.tenant_id),
            object_metadata_id=_to_uuid(model.object_metadata_id),
            field_type=RuntimeSchemaFieldType(model.type),
            name_field=model.name_field,
            label=model.label,
            default_value=model.default_value,
            description=model.description,
            icon=model.icon,
            options=model.options,
            settings=model.settings,
            is_custom=model.is_custom,
            is_active=model.is_active,
            is_system=model.is_system,
            is_ui_read_only=model.is_ui_read_only,
            is_nullable=model.is_nullable,
            is_unique=model.is_unique,
            relation_target_field_metadata_id=_to_uuid(
                model.relation_target_field_metadata_id
            ),
            relation_target_object_metadata_id=_to_uuid(
                model.relation_target_object_metadata_id
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def _to_uuid(value: UUID | str | None) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    return UUID(str(value))
