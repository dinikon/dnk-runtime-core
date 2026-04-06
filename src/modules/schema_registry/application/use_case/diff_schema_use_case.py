from src.modules.shared import EntityIdVO
from src.modules.schema_registry.domain.migration.diff_service import SchemaDiffService
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.application.service.postgres_schema_service import (
    PostgresSchemaService,
)
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.application.command.diff_schema_command import (
    DiffSchemaCommand,
)
from src.modules.schema_registry.domain.service.schema_registry_metadata_service import (
    SchemaRegistryMetadataService,
)


class DiffSchemaUseCase:

    def __init__(
        self,
        *,
        schema_seed_service: SchemaSeedService,
        data_source_service: DataSourceService,
        schema_diff_service: SchemaDiffService,
        postgres_schema_service: PostgresSchemaService,
        schema_registry_metadata_service: SchemaRegistryMetadataService,
    ) -> None:
        self._schema_seed_service = schema_seed_service
        self._data_source_service = data_source_service
        self._schema_diff_service = schema_diff_service
        self._postgres_schema_service = postgres_schema_service
        self._schema_registry_metadata_service = schema_registry_metadata_service

    async def execute(self, command: DiffSchemaCommand) -> None:
        tenant_id = EntityIdVO.from_value(command.tenant_id)
        seed = await self._schema_seed_service.load(seed_path=command.seed_path)
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id
        )
        actual_schema = await self._postgres_schema_service.inspect_schema(
            schema_name=datasource.schema_name.value
        )
        plan = self._schema_diff_service.build_diff_plan(
            schema_name=datasource.schema_name.value,
            seed=seed,
            actual_schema=actual_schema,
        )
        await self._postgres_schema_service.apply_plan(plan=plan)
        await self._schema_registry_metadata_service.replace_from_seed(
            tenant_id=tenant_id,
            seed=seed,
        )
