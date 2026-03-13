from __future__ import annotations

from datetime import UTC, datetime

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.application.field_definition.dto import (
    CreateFieldCommandDTO,
    DeleteFieldCommandDTO,
    FieldDefinitionDTO,
    UpdateFieldCommandDTO,
)
from src.modules.runtime_schema.application.object_definition.dto import (
    CreateObjectCommandDTO,
    DeleteObjectCommandDTO,
    ObjectDefinitionDTO,
    UpdateObjectCommandDTO,
)
from src.modules.runtime_schema.application.ports.orchestrator import (
    DdlOrchestratorServiceProtocol,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
    SyncTenantSystemSchemaResultDTO,
)
from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import (
    FieldIdVO,
    FieldName,
    FieldTypeVO,
)
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.object.value_object import (
    ObjectIdVO,
    ObjectLabelVO,
    ObjectNameVO,
)
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.contracts import (
    DdlDiffEngineProtocol,
    DdlExecutorProtocol,
    DdlPlanBuilderProtocol,
    FieldLayoutCompilerProtocol,
    FieldMetadataRepositoryProtocol,
    MetadataCompilerProtocol,
    ObjectMetadataRepositoryProtocol,
    SchemaIntrospectorProtocol,
    SchemaLockServiceProtocol,
    SchemaMigrationJournalRepositoryProtocol,
    SchemaVersionEntry,
    SchemaVersionRepositoryProtocol,
    SystemModelRegistryReaderProtocol,
)
from src.modules.runtime_schema.infrastructure.ddl_executor import DdlExecutionError
from src.modules.runtime_schema.infrastructure.ddl_models import (
    DdlOperationKind,
    DdlPlan,
    ExecutionReport,
    MetadataBundle,
)
from src.modules.runtime_schema.infrastructure.field_serialization import (
    deserialize_field_default,
    deserialize_field_options,
    deserialize_field_settings,
)
from src.modules.runtime_schema.infrastructure.repositories import utc_now
from src.modules.shared.domain.errors import ValidationError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class DdlOrchestratorService(DdlOrchestratorServiceProtocol):
    def __init__(
        self,
        *,
        registry_reader: SystemModelRegistryReaderProtocol,
        metadata_compiler: MetadataCompilerProtocol,
        field_layout_compiler: FieldLayoutCompilerProtocol,
        schema_introspector: SchemaIntrospectorProtocol,
        ddl_diff_engine: DdlDiffEngineProtocol,
        ddl_plan_builder: DdlPlanBuilderProtocol,
        ddl_executor: DdlExecutorProtocol,
        schema_version_repository: SchemaVersionRepositoryProtocol,
        schema_migration_journal_repository: SchemaMigrationJournalRepositoryProtocol,
        schema_lock_service: SchemaLockServiceProtocol,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
        field_metadata_repository: FieldMetadataRepositoryProtocol,
    ):
        self._registry_reader = registry_reader
        self._metadata_compiler = metadata_compiler
        self._field_layout_compiler = field_layout_compiler
        self._schema_introspector = schema_introspector
        self._ddl_diff_engine = ddl_diff_engine
        self._ddl_plan_builder = ddl_plan_builder
        self._ddl_executor = ddl_executor
        self._schema_version_repository = schema_version_repository
        self._schema_migration_journal_repository = schema_migration_journal_repository
        self._schema_lock_service = schema_lock_service
        self._object_metadata_repository = object_metadata_repository
        self._field_metadata_repository = field_metadata_repository

    async def bootstrap_tenant_system_schema(
        self,
        dto: BootstrapTenantSystemSchemaCommandDTO,
    ) -> SyncTenantSystemSchemaResultDTO:
        sync_dto = SyncTenantSystemSchemaCommandDTO(
            tenant_id=dto.tenant_id,
            data_source_id=dto.data_source_id,
            schema=dto.schema,
        )
        return await self.sync_tenant_system_schema(sync_dto)

    async def sync_tenant_system_schema(
        self,
        dto: SyncTenantSystemSchemaCommandDTO,
    ) -> SyncTenantSystemSchemaResultDTO:
        tenant_id = EntityIdVO.from_value(dto.tenant_id)
        data_source_id = DataSourceIdVO.from_value(dto.data_source_id)
        schema = self._normalize_schema(dto.schema)

        async with self._schema_lock_service.lock(tenant_id=tenant_id, schema=schema):
            manifest = await self._registry_reader.load_system_manifest()
            metadata_bundle = self._metadata_compiler.compile_system_schema(
                manifest=manifest,
                tenant_id=tenant_id,
                data_source_id=data_source_id,
            )
            execution_report = await self._apply_bundle_to_schema(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema=schema,
                metadata_bundle=metadata_bundle,
                allow_destructive=False,
            )
            await self._upsert_system_metadata(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                metadata_bundle=metadata_bundle,
            )
            await self._schema_version_repository.upsert(
                SchemaVersionEntry(
                    tenant_id=tenant_id,
                    data_source_id=data_source_id,
                    schema=schema,
                    version=metadata_bundle.version,
                    manifest_hash=metadata_bundle.manifest_hash,
                    updated_at=utc_now(),
                )
            )
            if execution_report.journal_entries:
                await self._schema_migration_journal_repository.add_entries(
                    tenant_id=tenant_id,
                    data_source_id=data_source_id,
                    schema=schema,
                    entries=list(execution_report.journal_entries),
                )

        return self._sync_result(
            report=execution_report,
            version=metadata_bundle.version,
            manifest_hash=metadata_bundle.manifest_hash,
        )

    async def create_object_definition(
        self,
        dto: CreateObjectCommandDTO,
    ) -> ObjectDefinitionDTO:
        tenant_id = EntityIdVO.from_value(dto.tenant_id)
        data_source_id = DataSourceIdVO.from_value(dto.data_source_id)

        object_name = ObjectNameVO.from_singular(
            dto.object_name_singular,
            plural=dto.object_name_plural,
        )
        object_label = (
            ObjectLabelVO(
                name_singular=dto.object_label_singular,
                name_plural=dto.object_label_plural,
            )
            if dto.object_label_singular and dto.object_label_plural
            else ObjectLabelVO.from_name(object_name)
        )
        if await self._object_metadata_repository.get_by_name(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            object_name_singular=object_name.name_singular,
        ):
            raise ValidationError(
                f"object '{object_name.name_singular}' already exists for tenant"
            )

        object_entity = ObjectMetadataEntity.create(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            object_name=object_name,
            object_label=object_label,
            description=dto.description,
            icon=dto.icon,
            shortcut=dto.shortcut,
            duplicate_criteria=dto.duplicate_criteria,
        )
        await self._object_metadata_repository.add(object_entity)

        if dto.schema:
            await self._sync_tenant_layout(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema=dto.schema,
                allow_destructive=False,
            )
        return self._object_to_dto(object_entity)

    async def update_object_definition(
        self,
        dto: UpdateObjectCommandDTO,
    ) -> ObjectDefinitionDTO:
        tenant_id = EntityIdVO.from_value(dto.tenant_id)
        object_id = ObjectIdVO.from_value(dto.object_id)
        object_entity = await self._object_metadata_repository.get_by_id(object_id=object_id)
        if object_entity is None:
            raise ValidationError(f"object '{dto.object_id}' was not found")
        if object_entity.tenant_id != tenant_id:
            raise ValidationError("object tenant mismatch")

        renamed_from_table: str | None = None
        if dto.object_name_singular is not None:
            previous_table_name = object_entity.object_name.name_plural
            next_name = ObjectNameVO.from_singular(
                dto.object_name_singular,
                plural=dto.object_name_plural
                or object_entity.object_name.name_plural,
            )
            if next_name != object_entity.object_name and not dto.allow_ddl_rename:
                raise ValidationError(
                    "object rename requires allow_ddl_rename=true"
                )
            next_label = (
                ObjectLabelVO(
                    name_singular=dto.object_label_singular,
                    name_plural=dto.object_label_plural,
                )
                if dto.object_label_singular and dto.object_label_plural
                else ObjectLabelVO.from_name(next_name)
            )
            object_entity.rename(object_name=next_name, object_label=next_label)
            if previous_table_name != next_name.name_plural:
                renamed_from_table = previous_table_name
        elif dto.object_label_singular and dto.object_label_plural:
            object_entity.object_label = ObjectLabelVO(
                name_singular=dto.object_label_singular,
                name_plural=dto.object_label_plural,
            )
            object_entity.touch()

        if dto.description is not None:
            object_entity.description = dto.description
        if dto.icon is not None:
            object_entity.icon = dto.icon
        if dto.shortcut is not None:
            object_entity.shortcut = dto.shortcut
        if dto.duplicate_criteria is not None:
            object_entity.duplicate_criteria = dto.duplicate_criteria
        object_entity.touch()

        await self._object_metadata_repository.save(object_entity)
        if dto.schema:
            normalized_schema = self._normalize_schema(dto.schema)
            if renamed_from_table is not None and dto.allow_ddl_rename:
                rename_builder = getattr(
                    self._ddl_plan_builder,
                    "build_rename_table_operation",
                    None,
                )
                if callable(rename_builder):
                    operation = rename_builder(
                        schema=normalized_schema,
                        old_table_name=renamed_from_table,
                        new_table_name=object_entity.object_name.name_plural,
                    )
                    rename_report = await self._execute_ddl_plan(
                        tenant_id=tenant_id,
                        data_source_id=object_entity.data_source_id,
                        schema=normalized_schema,
                        plan=DdlPlan(operations=(operation,)),
                    )
                    if rename_report.journal_entries:
                        await self._schema_migration_journal_repository.add_entries(
                            tenant_id=tenant_id,
                            data_source_id=object_entity.data_source_id,
                            schema=normalized_schema,
                            entries=list(rename_report.journal_entries),
                        )
            await self._sync_tenant_layout(
                tenant_id=tenant_id,
                data_source_id=object_entity.data_source_id,
                schema=normalized_schema,
                allow_destructive=False,
            )
        return self._object_to_dto(object_entity)

    async def delete_object_definition(self, dto: DeleteObjectCommandDTO) -> None:
        tenant_id = EntityIdVO.from_value(dto.tenant_id)
        object_id = ObjectIdVO.from_value(dto.object_id)
        object_entity = await self._object_metadata_repository.get_by_id(object_id=object_id)
        if object_entity is None:
            raise ValidationError(f"object '{dto.object_id}' was not found")
        if object_entity.tenant_id != tenant_id:
            raise ValidationError("object tenant mismatch")

        object_fields = await self._field_metadata_repository.list_by_object(
            object_id=object_entity.id
        )
        for field_entity in object_fields:
            await self._field_metadata_repository.delete(field_id=field_entity.id)
        await self._object_metadata_repository.delete(object_id=object_entity.id)

        if dto.schema:
            await self._sync_tenant_layout(
                tenant_id=tenant_id,
                data_source_id=object_entity.data_source_id,
                schema=dto.schema,
                allow_destructive=dto.allow_destructive,
            )

    async def create_field_definition(
        self,
        dto: CreateFieldCommandDTO,
    ) -> FieldDefinitionDTO:
        tenant_id = EntityIdVO.from_value(dto.tenant_id)
        object_id = ObjectIdVO.from_value(dto.object_id)
        object_entity = await self._object_metadata_repository.get_by_id(object_id=object_id)
        if object_entity is None:
            raise ValidationError(f"object '{dto.object_id}' was not found")
        if object_entity.tenant_id != tenant_id:
            raise ValidationError("object tenant mismatch")

        if await self._field_metadata_repository.get_by_object_and_name(
            object_id=object_id,
            field_name=dto.field_name,
        ):
            raise ValidationError(
                f"field '{dto.field_name}' already exists for object '{dto.object_id}'"
            )

        try:
            field_type = FieldTypeVO(dto.field_type.strip().lower())
            options = deserialize_field_options(field_type=field_type, payload=dto.options)
            settings = deserialize_field_settings(field_type=field_type, payload=dto.settings)
            default_value = deserialize_field_default(
                field_type=field_type,
                payload=dto.default_value,
            )
            relation_target_object_id = (
                ObjectIdVO.from_value(dto.relation_target_object_id)
                if dto.relation_target_object_id is not None
                else None
            )
            relation_target_field_id = (
                FieldIdVO.from_value(dto.relation_target_field_id)
                if dto.relation_target_field_id is not None
                else None
            )
        except Exception as exc:
            raise ValidationError(f"field definition is invalid: {exc}") from exc
        await self._validate_relation_target(
            tenant_id=tenant_id,
            field_type=field_type,
            relation_target_object_id=relation_target_object_id,
            relation_target_field_id=relation_target_field_id,
        )
        field_entity = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_id,
            field_type=field_type,
            field_name=FieldName(dto.field_name),
            label=dto.label,
            description=dto.description,
            icon=dto.icon,
            is_unique=dto.is_unique,
            is_index=dto.is_index,
            is_nullable=dto.is_nullable,
            is_ui_read_only=dto.is_ui_read_only,
            is_searchable=dto.is_searchable,
            options=options,
            settings=settings,
            default_value=default_value,
            relation_target_object_id=relation_target_object_id,
            relation_target_field_id=relation_target_field_id,
        )
        await self._field_metadata_repository.add(field_entity)

        if dto.schema:
            await self._sync_tenant_layout(
                tenant_id=tenant_id,
                data_source_id=object_entity.data_source_id,
                schema=dto.schema,
                allow_destructive=False,
            )
        return self._field_to_dto(field_entity)

    async def update_field_definition(
        self,
        dto: UpdateFieldCommandDTO,
    ) -> FieldDefinitionDTO:
        tenant_id = EntityIdVO.from_value(dto.tenant_id)
        field_id = FieldIdVO.from_value(dto.field_id)
        field_entity = await self._field_metadata_repository.get_by_id(field_id=field_id)
        if field_entity is None:
            raise ValidationError(f"field '{dto.field_id}' was not found")
        if field_entity.tenant_id != tenant_id:
            raise ValidationError("field tenant mismatch")

        if dto.label is not None:
            field_entity.label = dto.label
        if dto.description is not None:
            field_entity.description = dto.description
        if dto.icon is not None:
            field_entity.icon = dto.icon
        if dto.is_unique is not None:
            field_entity.is_unique = dto.is_unique
        if dto.is_index is not None:
            field_entity.is_index = dto.is_index
        if dto.is_nullable is not None:
            field_entity.is_nullable = dto.is_nullable
        if dto.is_ui_read_only is not None:
            field_entity.is_ui_read_only = dto.is_ui_read_only
        if dto.is_searchable is not None:
            field_entity.is_searchable = dto.is_searchable

        if dto.options is not None:
            try:
                options = deserialize_field_options(
                    field_type=field_entity.field_type,
                    payload=dto.options,
                )
            except Exception as exc:
                raise ValidationError(f"field options are invalid: {exc}") from exc
            field_entity.set_options(options)
        if dto.settings is not None:
            try:
                settings = deserialize_field_settings(
                    field_type=field_entity.field_type,
                    payload=dto.settings,
                )
            except Exception as exc:
                raise ValidationError(f"field settings are invalid: {exc}") from exc
            field_entity.set_settings(settings)
        if dto.default_value is not None:
            try:
                default_value = deserialize_field_default(
                    field_type=field_entity.field_type,
                    payload=dto.default_value,
                )
            except Exception as exc:
                raise ValidationError(f"field default_value is invalid: {exc}") from exc
            field_entity.set_default_value(default_value)

        if dto.relation_target_object_id is not None or dto.relation_target_field_id is not None:
            relation_target_object_id = (
                ObjectIdVO.from_value(dto.relation_target_object_id)
                if dto.relation_target_object_id is not None
                else field_entity.relation_target_object_id
            )
            relation_target_field_id = (
                FieldIdVO.from_value(dto.relation_target_field_id)
                if dto.relation_target_field_id is not None
                else field_entity.relation_target_field_id
            )
            await self._validate_relation_target(
                tenant_id=tenant_id,
                field_type=field_entity.field_type,
                relation_target_object_id=relation_target_object_id,
                relation_target_field_id=relation_target_field_id,
            )
            field_entity.set_relation_target(
                target_object_id=relation_target_object_id,
                target_field_id=relation_target_field_id,
            )

        self._ensure_field_mutation_consistency(field_entity)
        field_entity.touch()
        await self._field_metadata_repository.save(field_entity)

        object_entity = await self._object_metadata_repository.get_by_id(
            object_id=field_entity.object_metadata_id
        )
        if object_entity is None:
            raise ValidationError(
                f"object '{field_entity.object_metadata_id.value}' for field was not found"
            )
        if dto.schema:
            await self._sync_tenant_layout(
                tenant_id=tenant_id,
                data_source_id=object_entity.data_source_id,
                schema=dto.schema,
                allow_destructive=False,
            )
        return self._field_to_dto(field_entity)

    async def delete_field_definition(self, dto: DeleteFieldCommandDTO) -> None:
        tenant_id = EntityIdVO.from_value(dto.tenant_id)
        field_id = FieldIdVO.from_value(dto.field_id)
        field_entity = await self._field_metadata_repository.get_by_id(field_id=field_id)
        if field_entity is None:
            raise ValidationError(f"field '{dto.field_id}' was not found")
        if field_entity.tenant_id != tenant_id:
            raise ValidationError("field tenant mismatch")

        await self._field_metadata_repository.delete(field_id=field_entity.id)

        object_entity = await self._object_metadata_repository.get_by_id(
            object_id=field_entity.object_metadata_id
        )
        if object_entity is None:
            return
        if dto.schema:
            await self._sync_tenant_layout(
                tenant_id=tenant_id,
                data_source_id=object_entity.data_source_id,
                schema=dto.schema,
                allow_destructive=dto.allow_destructive,
            )

    async def _apply_bundle_to_schema(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema: str,
        metadata_bundle: MetadataBundle,
        allow_destructive: bool,
    ) -> ExecutionReport:
        expected_snapshot = self._field_layout_compiler.compile_layout(
            objects=list(metadata_bundle.objects),
            fields=list(metadata_bundle.fields),
        )
        actual_snapshot = await self._schema_introspector.introspect(schema=schema)
        diff = self._ddl_diff_engine.diff(
            expected=expected_snapshot,
            actual=actual_snapshot,
            allow_destructive=allow_destructive,
        )
        plan = self._ddl_plan_builder.build(schema=schema, diff=diff)
        if plan.is_empty():
            return ExecutionReport(operations=tuple(), journal_entries=tuple())
        return await self._execute_ddl_plan(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            schema=schema,
            plan=plan,
        )

    async def _sync_tenant_layout(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema: str,
        allow_destructive: bool,
    ) -> ExecutionReport:
        normalized_schema = self._normalize_schema(schema)
        objects = await self._object_metadata_repository.list_by_tenant_data_source(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
        )
        fields = await self._field_metadata_repository.list_by_tenant(tenant_id=tenant_id)
        object_ids = {str(object_entity.id.value) for object_entity in objects}
        scoped_fields = [
            field for field in fields if str(field.object_metadata_id.value) in object_ids
        ]
        expected_snapshot = self._field_layout_compiler.compile_layout(
            objects=objects,
            fields=scoped_fields,
        )
        actual_snapshot = await self._schema_introspector.introspect(schema=normalized_schema)
        diff = self._ddl_diff_engine.diff(
            expected=expected_snapshot,
            actual=actual_snapshot,
            allow_destructive=allow_destructive,
        )
        plan = self._ddl_plan_builder.build(
            schema=normalized_schema,
            diff=diff,
        )
        if plan.is_empty():
            return ExecutionReport(operations=tuple(), journal_entries=tuple())
        report = await self._execute_ddl_plan(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            schema=normalized_schema,
            plan=plan,
        )
        if report.journal_entries:
            await self._schema_migration_journal_repository.add_entries(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema=normalized_schema,
                entries=list(report.journal_entries),
            )
        return report

    async def _upsert_system_metadata(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        metadata_bundle: MetadataBundle,
    ) -> None:
        existing_objects = await self._object_metadata_repository.list_by_tenant_data_source(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
        )
        existing_object_by_name = {
            entity.object_name.name_singular: entity for entity in existing_objects
        }
        object_id_remap: dict[str, ObjectIdVO] = {}
        persisted_objects_by_key: dict[str, ObjectMetadataEntity] = {}

        for object_key, object_entity in metadata_bundle.objects_by_key.items():
            existing = existing_object_by_name.get(object_entity.object_name.name_singular)
            original_id = object_entity.id
            if existing is not None:
                object_entity.id = existing.id
                object_entity.created_at = existing.created_at
                object_entity.updated_at = datetime.now(UTC)
            await self._object_metadata_repository.save(object_entity)
            object_id_remap[str(original_id.value)] = object_entity.id
            persisted_objects_by_key[object_key] = object_entity

        existing_fields = await self._field_metadata_repository.list_by_tenant(tenant_id=tenant_id)
        existing_field_by_object_and_name = {
            (str(field.object_metadata_id.value), field.field_name.value): field
            for field in existing_fields
        }
        field_id_remap: dict[str, FieldIdVO] = {}

        for object_key, object_fields in metadata_bundle.fields_by_object_key.items():
            persisted_object = persisted_objects_by_key[object_key]
            for field_entity in object_fields:
                original_field_id = field_entity.id
                field_entity.object_metadata_id = persisted_object.id
                if field_entity.relation_target_object_id is not None:
                    remapped_relation_object_id = object_id_remap.get(
                        str(field_entity.relation_target_object_id.value)
                    )
                    if remapped_relation_object_id is not None:
                        field_entity.relation_target_object_id = remapped_relation_object_id

                existing = existing_field_by_object_and_name.get(
                    (str(persisted_object.id.value), field_entity.field_name.value)
                )
                if existing is not None:
                    field_entity.id = existing.id
                    field_entity.created_at = existing.created_at
                    field_entity.updated_at = datetime.now(UTC)
                await self._field_metadata_repository.save(field_entity)
                existing_field_by_object_and_name[
                    (str(persisted_object.id.value), field_entity.field_name.value)
                ] = field_entity
                field_id_remap[str(original_field_id.value)] = field_entity.id

        for object_fields in metadata_bundle.fields_by_object_key.values():
            for field_entity in object_fields:
                if field_entity.relation_target_field_id is None:
                    continue
                remapped_target_field_id = field_id_remap.get(
                    str(field_entity.relation_target_field_id.value)
                )
                if remapped_target_field_id is None:
                    continue
                if remapped_target_field_id == field_entity.relation_target_field_id:
                    continue
                field_entity.relation_target_field_id = remapped_target_field_id
                field_entity.updated_at = datetime.now(UTC)
                await self._field_metadata_repository.save(field_entity)

    @staticmethod
    def _normalize_schema(schema: object) -> str:
        if not isinstance(schema, str):
            raise ValidationError("schema is required")
        normalized = schema.strip().lower()
        if not normalized:
            raise ValidationError("schema is required")
        return normalized

    async def _validate_relation_target(
        self,
        *,
        tenant_id: EntityIdVO,
        field_type: FieldTypeVO,
        relation_target_object_id: ObjectIdVO | None,
        relation_target_field_id: FieldIdVO | None,
    ) -> None:
        if field_type != FieldTypeVO.RELATION:
            return
        if relation_target_object_id is None:
            return

        target_object = await self._object_metadata_repository.get_by_id(
            object_id=relation_target_object_id
        )
        if target_object is None:
            raise ValidationError(
                f"relation target object '{relation_target_object_id.value}' was not found"
            )
        if target_object.tenant_id != tenant_id:
            raise ValidationError("relation target object tenant mismatch")

        if relation_target_field_id is None:
            return
        target_field = await self._field_metadata_repository.get_by_id(
            field_id=relation_target_field_id
        )
        if target_field is None:
            raise ValidationError(
                f"relation target field '{relation_target_field_id.value}' was not found"
            )
        if target_field.tenant_id != tenant_id:
            raise ValidationError("relation target field tenant mismatch")
        if target_field.object_metadata_id != relation_target_object_id:
            raise ValidationError(
                "relation target field does not belong to relation target object"
            )

    @staticmethod
    def _sync_result(
        *,
        report: ExecutionReport,
        version: str,
        manifest_hash: str,
    ) -> SyncTenantSystemSchemaResultDTO:
        created_tables = 0
        added_columns = 0
        created_indexes = 0
        dropped_tables = 0
        dropped_columns = 0
        for operation in report.operations:
            if operation.kind == DdlOperationKind.CREATE_TABLE:
                created_tables += 1
            elif operation.kind == DdlOperationKind.ADD_COLUMN:
                added_columns += 1
            elif operation.kind == DdlOperationKind.CREATE_INDEX:
                created_indexes += 1
            elif operation.kind == DdlOperationKind.DROP_TABLE:
                dropped_tables += 1
            elif operation.kind == DdlOperationKind.DROP_COLUMN:
                dropped_columns += 1

        return SyncTenantSystemSchemaResultDTO(
            version=version,
            manifest_hash=manifest_hash,
            applied_operations=report.applied_operations,
            created_tables=created_tables,
            added_columns=added_columns,
            created_indexes=created_indexes,
            dropped_tables=dropped_tables,
            dropped_columns=dropped_columns,
        )

    @staticmethod
    def _object_to_dto(entity: ObjectMetadataEntity) -> ObjectDefinitionDTO:
        return ObjectDefinitionDTO(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            data_source_id=entity.data_source_id.value,
            object_name_singular=entity.object_name.name_singular,
            object_name_plural=entity.object_name.name_plural,
            object_label_singular=entity.object_label.name_singular,
            object_label_plural=entity.object_label.name_plural,
            description=entity.description,
            icon=entity.icon,
            shortcut=entity.shortcut,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def _field_to_dto(entity: FieldMetadataEntity) -> FieldDefinitionDTO:
        return FieldDefinitionDTO(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            object_id=entity.object_metadata_id.value,
            field_type=entity.field_type.value,
            field_name=entity.field_name.value,
            label=entity.label,
            description=entity.description,
            icon=entity.icon,
            is_unique=entity.is_unique,
            is_index=entity.is_index,
            is_nullable=entity.is_nullable,
            is_ui_read_only=entity.is_ui_read_only,
            is_searchable=entity.is_searchable,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def _ensure_field_mutation_consistency(field: FieldMetadataEntity) -> None:
        field.label = field.label.strip()
        if not field.label:
            raise ValidationError("field label is required")
        if field.description is not None:
            field.description = field.description.strip() or None
        if field.icon is not None:
            field.icon = field.icon.strip() or None
        if field.is_unique and not field.is_index:
            raise ValidationError("unique field must also be indexed")

    async def _execute_ddl_plan(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema: str,
        plan: DdlPlan,
    ) -> ExecutionReport:
        try:
            return await self._ddl_executor.execute(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema=schema,
                plan=plan,
            )
        except DdlExecutionError as exc:
            if exc.journal_entries:
                await self._schema_migration_journal_repository.add_entries(
                    tenant_id=tenant_id,
                    data_source_id=data_source_id,
                    schema=schema,
                    entries=list(exc.journal_entries),
                )
            raise ValidationError(f"ddl execution failed: {exc}") from exc


__all__ = ["DdlOrchestratorService"]
