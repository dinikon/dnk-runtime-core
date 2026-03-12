from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.custom_object.application.ports import (
    CreateCustomObjectDefinitionCommand,
    CreateCustomObjectFieldCommand,
    CustomObjectDefinition,
    CustomObjectFieldDefinition,
    CustomObjectSchemaRepositoryPort,
)
from src.modules.custom_object.domain import (
    CustomObjectDataSourceNotFoundError,
    CustomObjectNameVO,
    CustomObjectNotFoundError,
    CustomObjectRelationTargetNotFoundError,
)
from src.modules.runtime_schema.application.field_definition.dto import (
    CreateFieldCommandDTO,
)
from src.modules.runtime_schema.application.object_definition.dto import (
    CreateObjectCommandDTO,
)
from src.modules.runtime_schema.application.ports.orchestrator import (
    DdlOrchestratorServiceProtocol,
)
from src.modules.runtime_schema.domain.object.value_object import ObjectIdVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)


class RuntimeSchemaCustomObjectRepository(CustomObjectSchemaRepositoryPort):
    def __init__(
        self,
        *,
        session: AsyncSession,
        orchestrator: DdlOrchestratorServiceProtocol,
    ):
        self._session = session
        self._orchestrator = orchestrator
        self._object_repository = SqlAlchemyObjectMetadataRepository(session)

    async def create_object_definition(
        self,
        command: CreateCustomObjectDefinitionCommand,
    ) -> CustomObjectDefinition:
        object_name = CustomObjectNameVO(command.object_name_singular)
        data_source_model = await self._resolve_data_source(command.tenant_id)
        definition = await self._orchestrator.create_object_definition(
            CreateObjectCommandDTO(
                tenant_id=command.tenant_id,
                data_source_id=data_source_model.id,
                schema=data_source_model.schema,
                object_name_singular=object_name.value,
                object_name_plural=command.object_name_plural,
                object_label_singular=command.object_label_singular,
                object_label_plural=command.object_label_plural,
                description=command.description,
                icon=command.icon,
                shortcut=command.shortcut,
                is_system=False,
                is_custom=True,
                is_active=command.is_active,
                is_ui_read_only=command.is_ui_read_only,
            )
        )
        return CustomObjectDefinition(
            id=definition.id,
            object_name_singular=definition.object_name_singular,
            object_name_plural=definition.object_name_plural,
            object_label_singular=definition.object_label_singular,
            object_label_plural=definition.object_label_plural,
            description=definition.description,
            icon=definition.icon,
            shortcut=definition.shortcut,
            is_active=definition.is_active,
            is_ui_read_only=definition.is_ui_read_only,
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        )

    async def create_field_definition(
        self,
        command: CreateCustomObjectFieldCommand,
    ) -> CustomObjectFieldDefinition:
        object_name = CustomObjectNameVO(command.object_name_singular)
        data_source_model = await self._resolve_data_source(command.tenant_id)
        object_entity = await self._object_repository.get_by_name(
            tenant_id=EntityIdVO.from_value(command.tenant_id),
            data_source_id=DataSourceIdVO.from_value(data_source_model.id),
            object_name_singular=object_name.value,
        )
        if object_entity is None or not object_entity.is_active:
            raise CustomObjectNotFoundError(object_name.value)
        if object_entity.is_system or not object_entity.is_custom:
            raise CustomObjectNotFoundError(object_name.value)

        relation_target_object_id = await self._resolve_relation_target_object_id(
            tenant_id=command.tenant_id,
            data_source_id=data_source_model.id,
            target_object_name=command.relation_target_object_name,
        )

        definition = await self._orchestrator.create_field_definition(
            CreateFieldCommandDTO(
                tenant_id=command.tenant_id,
                object_id=object_entity.id.value,
                schema=data_source_model.schema,
                field_type=command.field_type,
                field_name=command.field_name,
                label=command.label,
                description=command.description,
                icon=command.icon,
                is_system=False,
                is_custom=True,
                is_active=command.is_active,
                is_unique=command.is_unique,
                is_index=command.is_index,
                is_nullable=command.is_nullable,
                is_ui_read_only=command.is_ui_read_only,
                is_searchable=command.is_searchable,
                options=command.options,
                settings=command.settings,
                default_value=command.default_value,
                relation_target_object_id=relation_target_object_id,
                relation_target_field_id=command.relation_target_field_id,
            )
        )
        return CustomObjectFieldDefinition(
            id=definition.id,
            object_id=definition.object_id,
            field_type=definition.field_type,
            field_name=definition.field_name,
            label=definition.label,
            description=definition.description,
            icon=definition.icon,
            is_active=definition.is_active,
            is_unique=definition.is_unique,
            is_index=definition.is_index,
            is_nullable=definition.is_nullable,
            is_ui_read_only=definition.is_ui_read_only,
            is_searchable=definition.is_searchable,
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        )

    async def _resolve_data_source(self, tenant_id: UUID) -> TenantDataSourceModel:
        data_source_model = await self._session.scalar(
            select(TenantDataSourceModel)
            .where(TenantDataSourceModel.tenant_id == str(tenant_id))
            .limit(1)
        )
        if data_source_model is None:
            raise CustomObjectDataSourceNotFoundError(str(tenant_id))
        return data_source_model

    async def _resolve_relation_target_object_id(
        self,
        *,
        tenant_id: UUID,
        data_source_id: UUID,
        target_object_name: str | None,
    ) -> UUID | None:
        if target_object_name is None:
            return None
        target_object = await self._object_repository.get_by_name(
            tenant_id=EntityIdVO.from_value(tenant_id),
            data_source_id=DataSourceIdVO.from_value(data_source_id),
            object_name_singular=target_object_name.strip().lower(),
        )
        if target_object is None or not target_object.is_active:
            raise CustomObjectRelationTargetNotFoundError(target_object_name)
        return ObjectIdVO.from_value(target_object.id.value).value


__all__ = ["RuntimeSchemaCustomObjectRepository"]
