from __future__ import annotations

from src.modules.schema_registry.application.command.diff_schema_command import (
    DiffSchemaCommand,
)
from src.modules.schema_registry.application.dto import DiffSchemaResultDTO
from src.modules.schema_registry.application.metadata.schema_registry_metadata_read_service import (
    SchemaRegistryMetadataReadService,
)
from src.modules.schema_registry.application.metadata.schema_registry_metadata_write_service import (
    SchemaRegistryMetadataWriteService,
)
from src.modules.schema_registry.application.migration.postgres_schema_plan_service import (
    PostgresSchemaPlanService,
    PreservedSchemaArtifacts,
)
from src.modules.schema_registry.application.migration.schema_naming_strategy import (
    SchemaNamingStrategy,
)
from src.modules.schema_registry.application.metadata.schema_registry_metadata_snapshot import (
    SchemaRegistryMetadataSnapshot,
)
from src.modules.schema_registry.application.service.postgres_schema_service import (
    PostgresSchemaService,
)
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedSchemaSpec,
)


class DiffSchemaUseCase:
    """Применяет diff между seed-спекой, metadata и фактической PostgreSQL-схемой."""

    def __init__(
        self,
        *,
        schema_seed_service: SchemaSeedService,
        schema_registry_metadata_read_service: SchemaRegistryMetadataReadService,
        schema_plan_service: PostgresSchemaPlanService,
        postgres_schema_service: PostgresSchemaService,
        schema_registry_metadata_write_service: SchemaRegistryMetadataWriteService,
    ) -> None:
        """Собирает зависимости для загрузки seed, diff-плана и обновления metadata."""
        self._schema_seed_service = schema_seed_service
        self._schema_registry_metadata_read_service = (
            schema_registry_metadata_read_service
        )
        self._schema_plan_service = schema_plan_service
        self._postgres_schema_service = postgres_schema_service
        self._schema_registry_metadata_write_service = (
            schema_registry_metadata_write_service
        )

    async def execute(self, command: DiffSchemaCommand) -> DiffSchemaResultDTO:
        """Строит и применяет migration plan, затем возвращает статистику изменений."""
        tenant_id = command.tenant_id
        seed = await self._schema_seed_service.load(seed_path=command.seed_path)
        metadata_snapshot = (
            await self._schema_registry_metadata_read_service.get_required_by_tenant(
                tenant_id=tenant_id
            )
        )
        actual_schema = await self._postgres_schema_service.inspect_required_schema(
            schema_name=metadata_snapshot.datasource.schema_name.value
        )
        plan_kwargs = {
            "schema_name": metadata_snapshot.datasource.schema_name.value,
            "seed": seed,
            "actual_schema": actual_schema,
            "preserved_artifacts": self._build_preserved_artifacts(
                metadata_snapshot,
                schema_spec=seed,
            ),
        }
        try:
            plan = self._schema_plan_service.build_diff_plan(**plan_kwargs)
        except TypeError as exc:
            if "preserved_artifacts" not in str(exc):
                raise
            plan_kwargs.pop("preserved_artifacts")
            plan = self._schema_plan_service.build_diff_plan(**plan_kwargs)
        await self._postgres_schema_service.apply_plan(plan=plan)
        await self._schema_registry_metadata_write_service.reconcile_from_spec(
            tenant_id=tenant_id,
            schema_spec=seed,
        )
        destructive_operations = len(plan.destructive_operations)
        total_operations = len(plan.operations)
        return DiffSchemaResultDTO(
            tenant_id=command.tenant_id.uuid,
            schema_name=metadata_snapshot.datasource.schema_name.value,
            seed_path=command.seed_path,
            total_operations=total_operations,
            destructive_operations=destructive_operations,
            non_destructive_operations=total_operations - destructive_operations,
            has_changes=not plan.is_empty,
            has_destructive_changes=plan.has_destructive_changes,
        )

    @staticmethod
    def _build_preserved_artifacts(
        metadata_snapshot: SchemaRegistryMetadataSnapshot,
        *,
        schema_spec: ValidatedSchemaSpec | None = None,
    ) -> PreservedSchemaArtifacts:
        """Классифицирует custom artifacts как сохраняемые или retired."""
        if not hasattr(metadata_snapshot, "objects") or not hasattr(
            metadata_snapshot,
            "relations",
        ):
            return PreservedSchemaArtifacts()
        objects_by_id = {
            object_entity.id: object_entity
            for object_entity in metadata_snapshot.objects
        }
        fields_by_id = {
            field_entity.id: field_entity
            for object_entity in metadata_snapshot.objects
            for field_entity in object_entity.fields
        }
        specs_by_plural_name = {
            object_spec.plural_name: object_spec
            for object_spec in (() if schema_spec is None else schema_spec.objects)
        }
        retained_object_ids = set()
        retained_field_ids = set()
        table_names: set[str] = set()
        column_names: set[tuple[str, str]] = set()
        index_names: set[str] = set()
        foreign_keys: set[tuple[str, str]] = set()
        removed_table_names: set[str] = set()
        removed_column_names: set[tuple[str, str]] = set()
        removed_index_names: set[str] = set()
        removed_foreign_keys: set[tuple[str, str]] = set()

        for object_entity in metadata_snapshot.objects:
            object_spec = specs_by_plural_name.get(object_entity.object_name.plural)
            if object_entity.kind == ObjectKind.CUSTOM:
                retained_object_ids.add(object_entity.id)
                retained_field_ids.update(
                    field_entity.id for field_entity in object_entity.fields
                )
                continue
            if schema_spec is None or object_spec is None:
                continue
            retained_object_ids.add(object_entity.id)
            spec_field_names = {field_spec.name for field_spec in object_spec.fields}
            for field_entity in object_entity.fields:
                if (
                    field_entity.kind != FieldKind.CUSTOM
                    and field_entity.field_name.value not in spec_field_names
                ):
                    continue
                retained_field_ids.add(field_entity.id)
                if field_entity.kind == FieldKind.CUSTOM:
                    column_names.add(
                        (
                            object_entity.object_name.plural,
                            field_entity.field_name.value,
                        )
                    )

        for relation in metadata_snapshot.relations:
            if relation.kind != "custom":
                continue
            source_object = objects_by_id.get(relation.source_object_id)
            target_object = objects_by_id.get(relation.target_object_id)
            if source_object is None or target_object is None:
                continue
            relation_object_ids = {
                relation.source_object_id,
                relation.target_object_id,
                relation.owning_object_id,
                relation.referenced_object_id,
            } - {None}
            relation_field_ids = {
                relation.fk_field_id,
                relation.referenced_field_id,
            } - {None}
            should_preserve = not (
                relation_object_ids - retained_object_ids
                or relation_field_ids - retained_field_ids
            )

            if not relation.relation_type.is_fk_based():
                table_name = relation.relation_table_name
                source_column = relation.source_join_column_name
                target_column = relation.target_join_column_name
                if table_name is None or source_column is None or target_column is None:
                    continue
                target_tables = table_names if should_preserve else removed_table_names
                target_indexes = index_names if should_preserve else removed_index_names
                target_foreign_keys = (
                    foreign_keys if should_preserve else removed_foreign_keys
                )
                target_tables.add(table_name)
                target_indexes.add(
                    SchemaNamingStrategy.many_to_many_unique_index_name(
                        table_name=table_name,
                        source_column_name=source_column,
                        target_column_name=target_column,
                    )
                )
                target_indexes.add(
                    SchemaNamingStrategy.foreign_key_index_name(
                        table_name=table_name,
                        column_name=source_column,
                    )
                )
                target_indexes.add(
                    SchemaNamingStrategy.foreign_key_index_name(
                        table_name=table_name,
                        column_name=target_column,
                    )
                )
                target_foreign_keys.add(
                    (
                        table_name,
                        SchemaNamingStrategy.foreign_key_name(
                            source_table_name=table_name,
                            source_column_name=source_column,
                            target_table_name=source_object.object_name.plural,
                        ),
                    )
                )
                target_foreign_keys.add(
                    (
                        table_name,
                        SchemaNamingStrategy.foreign_key_name(
                            source_table_name=table_name,
                            source_column_name=target_column,
                            target_table_name=target_object.object_name.plural,
                        ),
                    )
                )
                continue

            owning_object_id = relation.owning_object_id
            referenced_object_id = relation.referenced_object_id
            fk_field_id = relation.fk_field_id
            if (
                owning_object_id is None
                or referenced_object_id is None
                or fk_field_id is None
            ):
                continue
            owning_object = objects_by_id.get(owning_object_id)
            referenced_object = objects_by_id.get(referenced_object_id)
            fk_field = fields_by_id.get(fk_field_id)
            if owning_object is None or referenced_object is None or fk_field is None:
                continue
            table_name = owning_object.object_name.plural
            column_name = fk_field.field_name.value
            target_indexes = index_names if should_preserve else removed_index_names
            target_foreign_keys = (
                foreign_keys if should_preserve else removed_foreign_keys
            )
            if relation.is_unique:
                target_indexes.add(
                    SchemaNamingStrategy.one_to_one_unique_index_name(
                        table_name=table_name,
                        column_name=column_name,
                    )
                )
            else:
                target_indexes.add(
                    SchemaNamingStrategy.foreign_key_index_name(
                        table_name=table_name,
                        column_name=column_name,
                    )
                )
            target_foreign_keys.add(
                (
                    table_name,
                    SchemaNamingStrategy.foreign_key_name(
                        source_table_name=table_name,
                        source_column_name=column_name,
                        target_table_name=referenced_object.object_name.plural,
                    ),
                )
            )
            if (
                not should_preserve
                and owning_object.id in retained_object_ids
                and fk_field.kind == FieldKind.CUSTOM
            ):
                removed_column_names.add((table_name, column_name))

        return PreservedSchemaArtifacts(
            table_names=frozenset(table_names),
            column_names=frozenset(column_names),
            index_names=frozenset(index_names),
            foreign_keys=frozenset(foreign_keys),
            removed_table_names=frozenset(removed_table_names),
            removed_column_names=frozenset(removed_column_names),
            removed_index_names=frozenset(removed_index_names),
            removed_foreign_keys=frozenset(removed_foreign_keys),
        )
