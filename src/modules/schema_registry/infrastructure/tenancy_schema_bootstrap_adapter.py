from __future__ import annotations

from src.modules.schema_registry.application.command.create_schema_command import (
    CreateSchemaCommand,
)
from src.modules.schema_registry.application.use_case.create_schema_use_case import (
    CreateSchemaUseCase,
)
from src.modules.shared import EntityIdVO
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContext,
    TenantSchemaBootstrapPort,
)


class SchemaRegistryTenantSchemaBootstrapAdapter(TenantSchemaBootstrapPort):
    """Адаптер tenancy bootstrap, запускающий CreateSchemaUseCase schema_registry."""

    def __init__(self, create_schema_use_case: CreateSchemaUseCase) -> None:
        """Инициализирует адаптер use case создания runtime-схемы."""
        self._create_schema_use_case = create_schema_use_case

    async def bootstrap(
        self,
        context: TenantSchemaBootstrapContext,
    ) -> None:
        """Создает runtime-схему tenant по контексту onboarding."""
        await self._create_schema_use_case.execute(
            CreateSchemaCommand(
                tenant_id=EntityIdVO.from_value(context.tenant_id),
                schema_name=context.schema_name,
                seed_path=context.seed_path,
            )
        )
