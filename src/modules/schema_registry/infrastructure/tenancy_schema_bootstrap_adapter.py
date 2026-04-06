from __future__ import annotations

from src.modules.schema_registry.application.command.create_schema_command import (
    CreateSchemaCommand,
)
from src.modules.schema_registry.application.use_case.create_schema_use_case import (
    CreateSchemaUseCase,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContext,
    TenantSchemaBootstrapPort,
)


class SchemaRegistryTenantSchemaBootstrapAdapter(TenantSchemaBootstrapPort):
    def __init__(self, create_schema_use_case: CreateSchemaUseCase) -> None:
        self._create_schema_use_case = create_schema_use_case

    async def bootstrap(
        self,
        *,
        context: TenantSchemaBootstrapContext,
    ) -> None:
        await self._create_schema_use_case.execute(
            CreateSchemaCommand(
                tenant_id=context.tenant_id,
                schema_name=context.schema_name,
                seed_path=context.seed_path,
            )
        )
