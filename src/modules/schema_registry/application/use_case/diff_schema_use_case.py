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
        plan = self._schema_plan_service.build_diff_plan(
            schema_name=metadata_snapshot.datasource.schema_name.value,
            seed=seed,
            actual_schema=actual_schema,
        )
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
