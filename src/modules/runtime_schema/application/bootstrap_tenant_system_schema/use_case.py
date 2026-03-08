from __future__ import annotations

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
    BootstrapTenantSystemSchemaResultDTO,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.schema_manager import (
    TenantSchemaManagerProtocol,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.system_definitions import (
    SystemObjectDefinitionsProviderProtocol,
)
from src.modules.runtime_schema.domain.entities import FieldMetadata, ObjectMetadata


class BootstrapTenantSystemSchemaUseCase:
    def __init__(
        self,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
        field_metadata_repository: FieldMetadataRepositoryProtocol,
        system_object_definitions_provider: SystemObjectDefinitionsProviderProtocol,
        tenant_schema_manager: TenantSchemaManagerProtocol,
    ):
        self._object_metadata_repository = object_metadata_repository
        self._field_metadata_repository = field_metadata_repository
        self._system_object_definitions_provider = system_object_definitions_provider
        self._tenant_schema_manager = tenant_schema_manager

    async def execute(
        self,
        dto: BootstrapTenantSystemSchemaCommandDTO,
    ) -> BootstrapTenantSystemSchemaResultDTO:
        objects_created = 0
        fields_created = 0

        for (
            object_definition
        ) in self._system_object_definitions_provider.get_system_objects():
            object_metadata = (
                await self._object_metadata_repository.get_by_tenant_and_name_singular(
                    dto.tenant_id,
                    object_definition.name_singular,
                )
            )
            if object_metadata is None:
                object_metadata = ObjectMetadata.create_system(
                    tenant_id=dto.tenant_id,
                    data_source_id=dto.data_source_id,
                    name_singular=object_definition.name_singular,
                    name_plural=object_definition.name_plural,
                    label_singular=object_definition.label_singular,
                    label_plural=object_definition.label_plural,
                    description=object_definition.description,
                    icon=object_definition.icon,
                    is_ui_read_only=object_definition.is_ui_read_only,
                    is_audit_logged=object_definition.is_audit_logged,
                    is_searchable=object_definition.is_searchable,
                    duplicate_criteria=object_definition.duplicate_criteria,
                    shortcut=object_definition.shortcut,
                )
                await self._object_metadata_repository.add(object_metadata)
                objects_created += 1

            for field_definition in object_definition.fields:
                field_metadata = (
                    await self._field_metadata_repository.get_by_object_and_name_field(
                        object_metadata.id,
                        field_definition.name_field,
                    )
                )
                if field_metadata is None:
                    field_metadata = FieldMetadata.create_system(
                        tenant_id=dto.tenant_id,
                        object_metadata_id=object_metadata.id,
                        field_type=field_definition.field_type,
                        name_field=field_definition.name_field,
                        label=field_definition.label,
                        default_value=field_definition.default_value,
                        description=field_definition.description,
                        icon=field_definition.icon,
                        options=field_definition.options,
                        settings=field_definition.settings,
                        is_ui_read_only=field_definition.is_ui_read_only,
                        is_nullable=field_definition.is_nullable,
                        is_unique=field_definition.is_unique,
                    )
                    await self._field_metadata_repository.add(field_metadata)
                    fields_created += 1

                if (
                    field_definition.name_field
                    == object_definition.label_identifier_field_name
                    and object_metadata.label_identifier_field_metadata_id
                    != field_metadata.id
                ):
                    object_metadata.bind_label_identifier_field(field_metadata.id)
                    await self._object_metadata_repository.save(object_metadata)

            for field_definition in object_definition.fields:
                if (
                    field_definition.relation_target_object_name_singular is None
                    or field_definition.relation_target_field_name is None
                ):
                    continue

                field_metadata = (
                    await self._field_metadata_repository.get_by_object_and_name_field(
                        object_metadata.id,
                        field_definition.name_field,
                    )
                )
                if field_metadata is None:
                    continue

                relation_target_object = await self._object_metadata_repository.get_by_tenant_and_name_singular(
                    dto.tenant_id,
                    field_definition.relation_target_object_name_singular,
                )
                if relation_target_object is None:
                    continue

                relation_target_field = (
                    await self._field_metadata_repository.get_by_object_and_name_field(
                        relation_target_object.id,
                        field_definition.relation_target_field_name,
                    )
                )
                if relation_target_field is None:
                    continue

                if (
                    field_metadata.relation_target_object_metadata_id
                    != relation_target_object.id
                    or field_metadata.relation_target_field_metadata_id
                    != relation_target_field.id
                ):
                    field_metadata.bind_relation(
                        relation_target_object.id,
                        relation_target_field.id,
                    )
                    await self._field_metadata_repository.save(field_metadata)

            await self._tenant_schema_manager.ensure_system_object(
                schema=dto.schema,
                object_definition=object_definition,
            )

        return BootstrapTenantSystemSchemaResultDTO(
            objects_created=objects_created,
            fields_created=fields_created,
        )
