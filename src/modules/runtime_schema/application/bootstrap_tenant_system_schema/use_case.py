from __future__ import annotations

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
    BootstrapTenantSystemSchemaResultDTO,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
    RelationMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.schema_manager import (
    TenantSchemaManagerProtocol,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.system_definitions import (
    SystemObjectDefinitionsProviderProtocol,
)
from src.modules.runtime_schema.domain.entities import (
    FieldMetadata,
    ObjectMetadata,
    RelationMetadata,
    SystemFieldDefinition,
    SystemObjectDefinition,
)
from src.modules.runtime_schema.domain.errors import SystemRelationDefinitionError
from src.modules.runtime_schema.domain.value_objects.relation_kind import (
    RuntimeSchemaRelationKind,
)


class BootstrapTenantSystemSchemaUseCase:
    def __init__(
        self,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
        field_metadata_repository: FieldMetadataRepositoryProtocol,
        relation_metadata_repository: RelationMetadataRepositoryProtocol,
        system_object_definitions_provider: SystemObjectDefinitionsProviderProtocol,
        tenant_schema_manager: TenantSchemaManagerProtocol,
    ):
        self._object_metadata_repository = object_metadata_repository
        self._field_metadata_repository = field_metadata_repository
        self._relation_metadata_repository = relation_metadata_repository
        self._system_object_definitions_provider = system_object_definitions_provider
        self._tenant_schema_manager = tenant_schema_manager

    async def execute(
        self,
        dto: BootstrapTenantSystemSchemaCommandDTO,
    ) -> BootstrapTenantSystemSchemaResultDTO:
        objects_created = 0
        fields_created = 0

        object_definitions = (
            self._system_object_definitions_provider.get_system_objects()
        )

        for object_definition in object_definitions:
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
                    table_name=object_definition.table_name,
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

                await self._bind_label_identifier_field(
                    object_metadata=object_metadata,
                    object_definition=object_definition,
                    field_definition=field_definition,
                    field_metadata=field_metadata,
                )

            await self._tenant_schema_manager.ensure_system_object(
                schema=dto.schema,
                object_definition=object_definition,
            )

        for object_definition in object_definitions:
            await self._ensure_system_relations(
                tenant_id=dto.tenant_id,
                schema=dto.schema,
                object_definition=object_definition,
            )

        return BootstrapTenantSystemSchemaResultDTO(
            objects_created=objects_created,
            fields_created=fields_created,
        )

    async def _bind_label_identifier_field(
        self,
        *,
        object_metadata: ObjectMetadata,
        object_definition: SystemObjectDefinition,
        field_definition: SystemFieldDefinition,
        field_metadata: FieldMetadata,
    ) -> None:
        if field_definition.name_field != object_definition.label_identifier_field_name:
            return
        if object_metadata.label_identifier_field_metadata_id == field_metadata.id:
            return

        object_metadata.bind_label_identifier_field(field_metadata.id)
        await self._object_metadata_repository.save(object_metadata)

    async def _ensure_system_relations(
        self,
        *,
        tenant_id,
        schema: str,
        object_definition: SystemObjectDefinition,
    ) -> None:
        source_object = (
            await self._object_metadata_repository.get_by_tenant_and_name_singular(
                tenant_id,
                object_definition.name_singular,
            )
        )
        if source_object is None:
            return

        for field_definition in object_definition.fields:
            if not self._is_owner_relation(field_definition):
                continue
            if (
                field_definition.relation_target_object_name_singular is None
                or field_definition.relation_target_field_name is None
            ):
                raise SystemRelationDefinitionError(
                    object_definition.name_singular,
                    field_definition.name_field,
                    "missing relation target object or field name",
                )

            source_field = (
                await self._field_metadata_repository.get_by_object_and_name_field(
                    source_object.id,
                    field_definition.name_field,
                )
            )
            if source_field is None:
                raise SystemRelationDefinitionError(
                    object_definition.name_singular,
                    field_definition.name_field,
                    "source field metadata was not created",
                )

            target_object = (
                await self._object_metadata_repository.get_by_tenant_and_name_singular(
                    tenant_id,
                    field_definition.relation_target_object_name_singular,
                )
            )
            if target_object is None:
                raise SystemRelationDefinitionError(
                    object_definition.name_singular,
                    field_definition.name_field,
                    "target object metadata was not found",
                )

            target_field = (
                await self._field_metadata_repository.get_by_object_and_name_field(
                    target_object.id,
                    field_definition.relation_target_field_name,
                )
            )
            if target_field is None:
                raise SystemRelationDefinitionError(
                    object_definition.name_singular,
                    field_definition.name_field,
                    "target field metadata was not found",
                )

            if (
                source_field.relation_target_object_metadata_id != target_object.id
                or source_field.relation_target_field_metadata_id != target_field.id
            ):
                source_field.bind_relation(target_object.id, target_field.id)
                await self._field_metadata_repository.save(source_field)

            relation = await self._relation_metadata_repository.get_by_source_field_id(
                source_field.id
            )
            if relation is None:
                relation = self._build_system_relation(
                    tenant_id=tenant_id,
                    field_definition=field_definition,
                    source_object=source_object,
                    source_field=source_field,
                    target_object=target_object,
                    target_field=target_field,
                )
                await self._relation_metadata_repository.add(relation)
            elif self._relation_conflicts_with_definition(
                relation=relation,
                field_definition=field_definition,
                source_object=source_object,
                source_field=source_field,
                target_object=target_object,
                target_field=target_field,
            ):
                raise SystemRelationDefinitionError(
                    object_definition.name_singular,
                    field_definition.name_field,
                    "existing relation metadata conflicts with system definition",
                )

            await self._tenant_schema_manager.ensure_relation(
                schema=schema,
                relation=relation,
                source_object=source_object,
                source_field=source_field,
                target_object=target_object,
                target_field=target_field,
            )

    @staticmethod
    def _is_owner_relation(field_definition: SystemFieldDefinition) -> bool:
        return field_definition.relation_kind in {
            RuntimeSchemaRelationKind.MANY_TO_ONE,
            RuntimeSchemaRelationKind.ONE_TO_ONE,
        }

    @staticmethod
    def _build_system_relation(
        *,
        tenant_id,
        field_definition: SystemFieldDefinition,
        source_object: ObjectMetadata,
        source_field: FieldMetadata,
        target_object: ObjectMetadata,
        target_field: FieldMetadata,
    ) -> RelationMetadata:
        if field_definition.relation_kind == RuntimeSchemaRelationKind.ONE_TO_ONE:
            return RelationMetadata.create_one_to_one(
                tenant_id=tenant_id,
                source_object_metadata_id=source_object.id,
                source_field_metadata_id=source_field.id,
                target_object_metadata_id=target_object.id,
                target_field_metadata_id=target_field.id,
                reverse_name_field=field_definition.reverse_name_field,
                reverse_label=field_definition.reverse_label,
                on_delete=field_definition.relation_on_delete,
                is_required=not source_field.is_nullable,
                is_system=True,
            )

        return RelationMetadata.create_many_to_one(
            tenant_id=tenant_id,
            source_object_metadata_id=source_object.id,
            source_field_metadata_id=source_field.id,
            target_object_metadata_id=target_object.id,
            target_field_metadata_id=target_field.id,
            reverse_name_field=field_definition.reverse_name_field,
            reverse_label=field_definition.reverse_label,
            on_delete=field_definition.relation_on_delete,
            is_required=not source_field.is_nullable,
            is_system=True,
        )

    @staticmethod
    def _relation_conflicts_with_definition(
        *,
        relation: RelationMetadata,
        field_definition: SystemFieldDefinition,
        source_object: ObjectMetadata,
        source_field: FieldMetadata,
        target_object: ObjectMetadata,
        target_field: FieldMetadata,
    ) -> bool:
        return (
            not relation.is_active
            or relation.kind != field_definition.relation_kind
            or relation.source_object_metadata_id != source_object.id
            or relation.source_field_metadata_id != source_field.id
            or relation.target_object_metadata_id != target_object.id
            or relation.target_field_metadata_id != target_field.id
            or relation.reverse_name_field != field_definition.reverse_name_field
            or relation.reverse_label != field_definition.reverse_label
            or relation.on_delete != field_definition.relation_on_delete
            or relation.is_required != (not source_field.is_nullable)
        )
