from src.modules.shared import EntityIdVO
from src.modules.schema_registry.application.command.create_schema_command import (
    CreateSchemaCommand,
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


class CreateSchemaUseCase:

    def __init__(
        self,
        *,
        schema_seed_service: SchemaSeedService,
        schema_plan_service: PostgresSchemaPlanService,
        postgres_schema_service: PostgresSchemaService,
        schema_registry_metadata_write_service: SchemaRegistryMetadataWriteService,
    ) -> None:
        self._schema_seed_service = schema_seed_service
        self._schema_plan_service = schema_plan_service
        self._postgres_schema_service = postgres_schema_service
        self._schema_registry_metadata_write_service = (
            schema_registry_metadata_write_service
        )

    async def execute(self, command: CreateSchemaCommand) -> None:
        tenant_id = EntityIdVO.from_value(command.tenant_id)
        seed = await self._schema_seed_service.load(seed_path=command.seed_path)
        await self._postgres_schema_service.ensure_schema_absent(
            schema_name=command.schema_name
        )
        plan = self._schema_plan_service.build_create_plan(
            schema_name=command.schema_name,
            seed=seed,
        )
        await self._postgres_schema_service.apply_plan(plan=plan)
        await self._schema_registry_metadata_write_service.create_from_seed(
            tenant_id=tenant_id,
            schema_name=command.schema_name,
            seed=seed,
        )
