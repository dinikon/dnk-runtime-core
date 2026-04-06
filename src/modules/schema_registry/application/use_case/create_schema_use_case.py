from src.modules.shared import EntityIdVO
from src.modules.schema_registry.application.command.create_schema_command import (
    CreateSchemaCommand,
)
from src.modules.schema_registry.application.service.postgres_schema_service import (
    PostgresSchemaService,
)
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.domain.migration.diff_service import SchemaDiffService
from src.modules.schema_registry.domain.service.schema_registry_metadata_service import (
    SchemaRegistryMetadataService,
)


class CreateSchemaUseCase:

    def __init__(
        self,
        *,
        schema_seed_service: SchemaSeedService,
        schema_diff_service: SchemaDiffService,
        postgres_schema_service: PostgresSchemaService,
        schema_registry_metadata_service: SchemaRegistryMetadataService,
    ) -> None:
        self._schema_seed_service = schema_seed_service
        self._schema_diff_service = schema_diff_service
        self._postgres_schema_service = postgres_schema_service
        self._schema_registry_metadata_service = schema_registry_metadata_service

    async def execute(self, command: CreateSchemaCommand) -> None:
        tenant_id = EntityIdVO.from_value(command.tenant_id)
        seed = await self._schema_seed_service.load(seed_path=command.seed_path)
        await self._postgres_schema_service.ensure_schema_absent(
            schema_name=command.schema_name
        )
        plan = self._schema_diff_service.build_create_plan(
            schema_name=command.schema_name,
            seed=seed,
        )
        await self._postgres_schema_service.apply_plan(plan=plan)
        await self._schema_registry_metadata_service.create_from_seed(
            tenant_id=tenant_id,
            schema_name=command.schema_name,
            seed=seed,
        )
