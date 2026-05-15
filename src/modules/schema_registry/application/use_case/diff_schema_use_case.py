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
            "preserved_artifacts": self._build_preserved_artifacts(metadata_snapshot),
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
    ) -> PreservedSchemaArtifacts:
        """Собирает physical relation artifacts, которые seed diff не удаляет."""
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
        table_names: set[str] = set()
        index_names: set[str] = set()
        foreign_keys: set[tuple[str, str]] = set()

        for relation in metadata_snapshot.relations:
            source_object = objects_by_id.get(relation.source_object_id)
            target_object = objects_by_id.get(relation.target_object_id)
            if source_object is None or target_object is None:
                continue

            if not relation.relation_type.is_fk_based():
                table_name = relation.relation_table_name
                source_column = relation.source_join_column_name
                target_column = relation.target_join_column_name
                if table_name is None or source_column is None or target_column is None:
                    continue
                table_names.add(table_name)
                index_names.add(
                    SchemaNamingStrategy.many_to_many_unique_index_name(
                        table_name=table_name,
                        source_column_name=source_column,
                        target_column_name=target_column,
                    )
                )
                index_names.add(
                    SchemaNamingStrategy.foreign_key_index_name(
                        table_name=table_name,
                        column_name=source_column,
                    )
                )
                index_names.add(
                    SchemaNamingStrategy.foreign_key_index_name(
                        table_name=table_name,
                        column_name=target_column,
                    )
                )
                foreign_keys.add(
                    (
                        table_name,
                        SchemaNamingStrategy.foreign_key_name(
                            source_table_name=table_name,
                            source_column_name=source_column,
                            target_table_name=source_object.object_name.plural,
                        ),
                    )
                )
                foreign_keys.add(
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
            if relation.is_unique:
                index_names.add(
                    SchemaNamingStrategy.one_to_one_unique_index_name(
                        table_name=table_name,
                        column_name=column_name,
                    )
                )
            else:
                index_names.add(
                    SchemaNamingStrategy.foreign_key_index_name(
                        table_name=table_name,
                        column_name=column_name,
                    )
                )
            foreign_keys.add(
                (
                    table_name,
                    SchemaNamingStrategy.foreign_key_name(
                        source_table_name=table_name,
                        source_column_name=column_name,
                        target_table_name=referenced_object.object_name.plural,
                    ),
                )
            )

        return PreservedSchemaArtifacts(
            table_names=frozenset(table_names),
            index_names=frozenset(index_names),
            foreign_keys=frozenset(foreign_keys),
        )
